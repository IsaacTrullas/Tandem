import base64,json,time,unittest
from unittest.mock import patch
from urllib.parse import parse_qs,urlsplit
from tandem.source_client import SourceClient,SourceError,_allowed,SOURCE,SSO,LOGIN,AUTHORIZE,TOKEN,JWKS,CALLBACK,CLIENT_ID,ACCOUNTS
from tandem.credentials import save_credentials,CredentialError,TARGET

PUMPER='11111111-1111-4111-8111-111111111111'
DEVICE='22222222-2222-4222-8222-222222222222'

class Response:
    def __init__(self,data=None,status=200,headers=None):
        self.status_code=status;self.headers=headers or {}
        self.content=data if isinstance(data,bytes) else json.dumps(data or {}).encode()

class FakeSession:
    def __init__(self,mode=None):
        import jwt
        from cryptography.hazmat.primitives.asymmetric import rsa
        self.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        self.jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()));self.jwk['kid']='test-key'
        self.mode=mode;self.calls=[];self.closed=False
        self.events_body=b'{"events": [], "clockChanges": [], "newField": 42}'
    def close(self):self.closed=True
    def request(self,method,url,**kwargs):
        import jwt
        self.calls.append((method,url,kwargs))
        if url==SSO:return Response()
        if url==LOGIN:return Response({'status':'SUCCESS'})
        if url.startswith(AUTHORIZE+'?'):
            q=parse_qs(urlsplit(url).query);self.nonce=q['nonce'][0]
            self.assert_pkce=q['code_challenge_method']==['S256']
            if self.mode=='redirect':return Response(status=302,headers={'Location':'https://evil.example/steal'})
            state='tampered' if self.mode=='state' else q['state'][0]
            return Response(status=302,headers={'Location':CALLBACK+'?state='+state+'&code=test-code'})
        if url==TOKEN:
            claims={'sub':'test','iss':ACCOUNTS,'aud':CLIENT_ID,'iat':int(time.time()),
                'exp':int(time.time())+1200,'nonce':self.nonce,'pumperId':PUMPER}
            if self.mode=='nonce':claims['nonce']='different'
            if self.mode=='issuer':claims['iss']='https://evil.example'
            if self.mode=='audience':claims['aud']='different-client'
            if self.mode=='expired':claims['exp']=int(time.time())-100
            token=jwt.encode(claims,self.key,algorithm='RS256',headers={'kid':'test-key'})
            if self.mode=='signature':token=token[:-15]+'aaaaaaaaaaaaaaa'
            return Response({'access_token':'test-access','id_token':token,'expires_in':1200,'token_type':'Bearer'})
        if url==JWKS:return Response({'keys':[self.jwk]})
        if '/bff/pumper/' in url:return Response({'pumps':[{'assignmentId':DEVICE,'serialNumber':'SYNTHETIC'}]})
        if '/bff/pump-logs/' in url:return Response(self.events_body,status=401 if self.mode=='401' else 200)
        raise AssertionError('Unexpected test request')

class SourceClientTests(unittest.TestCase):
    def client(self,mode=None):
        session=FakeSession(mode)
        client=SourceClient('test@example.invalid','synthetic',session=session,sleeper=lambda _:None)
        self.addCleanup(client.close)
        return client,session
    def test_flow_and_raw_unknown_fields(self):
        c,s=self.client();self.assertTrue(s.assert_pkce)
        c.get_pumper();raw=c.get_pump_logs(DEVICE,'2026-10-01','2026-10-28')
        self.assertEqual(raw,s.events_body)
        query=parse_qs(urlsplit(s.calls[-1][1]).query)
        self.assertNotIn('eventCodes',query);self.assertNotIn('eventIds',query)
        self.assertEqual(query['startDate'],['2026-10-01T00:00:00Z'])
        self.assertFalse(s.trust_env)
        for method,url,kw in s.calls:
            self.assertFalse(kw['allow_redirects']);self.assertEqual(kw['timeout'],(10,45))
            if not url.startswith(SOURCE+'/api/reports/bff/'):
                self.assertNotIn('Authorization',kw['headers'])
    def test_strict_oidc_rejections(self):
        for mode in ('state','nonce','issuer','audience','expired','signature','redirect'):
            with self.subTest(mode=mode):
                s=FakeSession(mode)
                with self.assertRaises(SourceError) as caught:
                    SourceClient('test@example.invalid','secret-marker',session=s,sleeper=lambda _:None)
                self.assertTrue(s.closed)
                self.assertNotIn('secret-marker',str(caught.exception));self.assertNotIn('test-access',str(caught.exception))
                self.assertFalse(any('evil.example' in call[1] for call in s.calls))
    def test_patient_device_scope(self):
        c,s=self.client()
        with self.assertRaises(SourceError):c.get_pump_logs(DEVICE,'2026-10-01','2026-10-01')
        c.get_pumper()
        with self.assertRaises(SourceError):c.get_pump_logs(PUMPER,'2026-10-01','2026-10-01')
    def test_dates_bounded_and_ordered(self):
        c,s=self.client();c.get_pumper();count=len(s.calls)
        for start,end in [('2026-10-01','2026-10-29'),('2026-10-02','2026-10-01'),('bad','2026-10-01')]:
            with self.assertRaises(SourceError):c.get_pump_logs(DEVICE,start,end)
        self.assertEqual(len(s.calls),count)
    def test_mutations_and_external_hosts_denied(self):
        c,s=self.client();count=len(s.calls)
        for method,url in [('POST',SOURCE+'/api/reports/bff/pumper/'+PUMPER),('DELETE',LOGIN),
            ('GET','https://evil.example/'),('GET','http://source.eu.tandemdiabetes.com/'),
            ('POST',TOKEN+'?anything=1'),('GET',SOURCE+'/api/settings'),('GET',SOURCE+'/api/reports/bff/pumper/../settings')]:
            with self.subTest(method=method,url=url):
                with self.assertRaises(SourceError):c._request(method,url)
        self.assertEqual(len(s.calls),count)
    def test_unauthorized_stops_no_automatic_login_loop(self):
        c,s=self.client('401');c.get_pumper();n=len(s.calls)
        with self.assertRaises(SourceError):c.get_pump_logs(DEVICE,'2026-10-01','2026-10-01')
        self.assertEqual(len(s.calls),n+1)
    def test_expired_token_makes_no_request(self):
        c,s=self.client();c.get_pumper();c._expires=0;n=len(s.calls)
        with self.assertRaises(SourceError):c.get_pump_logs(DEVICE,'2026-10-01','2026-10-01')
        self.assertEqual(len(s.calls),n)
    def test_retry_bounded_and_rate_limit_respected(self):
        c,s=self.client();waits=[];c._sleep=waits.append
        with patch.object(s,'request',return_value=Response(status=503)) as request:
            r=c._request('GET',SSO)
            self.assertEqual(r.status_code,503);self.assertEqual(request.call_count,3);self.assertEqual(waits,[1,2])
        with patch.object(s,'request',return_value=Response(status=429,headers={'Retry-After':'120'})) as request:
            with self.assertRaises(SourceError):c._request('GET',SSO)
            self.assertEqual(request.call_count,1)
    def test_auth_post_not_retried(self):
        c,s=self.client()
        with patch.object(s,'request',side_effect=RuntimeError('sensitive transport error')) as request:
            with self.assertRaises(SourceError) as caught:c._request('POST',LOGIN,json={})
            self.assertEqual(request.call_count,1);self.assertNotIn('sensitive',str(caught.exception))
    def test_malformed_http200_bodies_return_for_collector_archival(self):
        c,s=self.client();c.get_pumper()
        for raw in (b'{"events": []}', b'not json', b'[]'):
            s.events_body=raw
            self.assertEqual(c.get_pump_logs(DEVICE,'2026-10-01','2026-10-01'),raw)
        with patch.object(s,'request',return_value=Response(b'bad pumper JSON')):
            self.assertEqual(c.get_pumper(),b'bad pumper JSON')
        self.assertEqual(c._devices,set())
    def test_safe_error_codes(self):
        self.assertEqual(SourceError('Safe',401).code,'authentication_required')
        self.assertEqual(SourceError('Safe',403).code,'access_denied')
        self.assertEqual(SourceError('Safe',500).code,'server_unavailable')
        c,s=self.client();c.get_pumper();c._expires=0
        with self.assertRaises(SourceError) as caught:c.get_pump_logs(DEVICE,'2026-10-01','2026-10-01')
        self.assertEqual(caught.exception.code,'session_expired')
    def test_close_clears_session_and_access_token(self):
        c,s=self.client();c.close();self.assertIsNone(c._token);self.assertIsNone(c._session);self.assertTrue(s.closed)

class CredentialValidationTests(unittest.TestCase):
    def test_invalid_credentials_never_access_windows_store(self):
        with patch('tandem.credentials._api') as api:
            for email,password in [('', 'x'),('a@b',''),('x','y'),('a@b','x'*1281),('a@b','bad\0pass')]:
                with self.assertRaises(CredentialError):save_credentials(email,password)
            api.assert_not_called()
    def test_scope_name(self):self.assertEqual(TARGET,'TandemLocal:EU')

if __name__=='__main__':unittest.main()
