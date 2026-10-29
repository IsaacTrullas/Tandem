"""Read-only Tandem Source EU client.

Endpoint/protocol research: github.com/jwoglom/tconnectsync, MIT, James Woglom.
This implementation never imports/runs that synchronizer. Authentication is the
only POST capability; therapy/settings endpoints have no write capability.
Tokens/cookies are memory-only. Device times are returned without conversion.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import date
from urllib.parse import urlsplit, urljoin, urlencode, parse_qs
from uuid import UUID

SOURCE = 'https://source.eu.tandemdiabetes.com'
SSO = 'https://sso.tandemdiabetes.com/'
ACCOUNTS = 'https://tdcservices.eu.tandemdiabetes.com/accounts/api'
LOGIN = ACCOUNTS + '/login'
AUTHORIZE = ACCOUNTS + '/connect/authorize'
TOKEN = ACCOUNTS + '/connect/token'
JWKS = ACCOUNTS + '/.well-known/openid-configuration/jwks'
CALLBACK = SOURCE + '/authorize/callback'
CLIENT_ID = '1519e414-eeec-492e-8c5e-97bea4815a10'
TIMEOUT = (10, 45)
MAX_BODY = 128 * 1024 * 1024

class SourceError(RuntimeError):
    """Sanitized error; response text, URLs, credentials and tokens omitted."""
    def __init__(self, message, status=None, *, code=None):
        super().__init__(message)
        self.status = status
        self.code = code or ({401:'authentication_required',403:'access_denied',404:'endpoint_unavailable',
            429:'rate_limited'}.get(status) or ('server_unavailable' if status and status >= 500 else 'source_error'))


def _uuid(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise SourceError('Identificador de dispositivo o paciente no válido', code='invalid_identifier') from None


def _allowed(method, url):
    try:
        p = urlsplit(url)
        port = p.port
    except ValueError:
        return False
    if p.scheme != 'https' or port not in (None, 443) or p.username or p.password or p.fragment:
        return False
    base = p.scheme + '://' + p.netloc + p.path
    if method == 'POST':
        return base in (LOGIN, TOKEN) and not p.query
    if method != 'GET':
        return False
    if base in (SSO, AUTHORIZE, JWKS, ACCOUNTS + '/connect/authorize/callback'):
        return True
    if p.netloc == 'source.eu.tandemdiabetes.com':
        for prefix in ('/api/reports/bff/pumper/', '/api/reports/bff/pump-logs/'):
            if p.path.startswith(prefix):
                try:
                    return str(UUID(p.path[len(prefix):])) == p.path[len(prefix):].lower()
                except ValueError:
                    return False
    return False


class SourceClient:
    """EU only. Call get_pumper before get_pump_logs. No persistent session cache."""
    def __init__(self, email, password, *, session=None, sleeper=time.sleep):
        if not email or not password:
            raise SourceError('Faltan las credenciales de Tandem', code='missing_credentials')
        if session is None:
            try:
                import requests
            except ImportError:
                raise SourceError('Instale las dependencias de conexión de la aplicación', code='missing_dependency') from None
            session = requests.Session()
        self._session = session
        self._session.trust_env = False  # No implicit netrc or proxy credentials.
        self._sleep = sleeper
        self._token = None
        self._expires = 0
        self._devices = set()
        self.pumper_id = None
        try:
            self._login(email, password)
        except Exception:
            self.close()
            raise

    def close(self):
        self._token = None
        self._expires = 0
        self._devices.clear()
        if self._session is not None:
            if hasattr(self._session, 'cookies'):
                self._session.cookies.clear()
            self._session.close()
            self._session = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _request(self, method, url, *, authorized=False, **kwargs):
        if not _allowed(method, url):
            raise SourceError('Operación remota fuera del permiso de solo lectura', code='operation_denied')
        if self._session is None:
            raise SourceError('La conexión está cerrada', code='connection_closed')
        origin = SOURCE if authorized else SSO.rstrip('/')
        headers = {'User-Agent': 'TandemLocal/0.5', 'Accept': 'application/json',
                   'Origin': origin, 'Referer': origin + '/'}
        if authorized:
            if not url.startswith(SOURCE + '/api/reports/bff/'):
                raise SourceError('Destino no autorizado para la sesión', code='operation_denied')
            if not self._token or time.time() >= self._expires - 10:
                raise SourceError('Sesión caducada; vuelva a ejecutar la actualización', 401, code='session_expired')
            headers['Authorization'] = 'Bearer ' + self._token
        attempts = 3 if method == 'GET' else 1
        for attempt in range(attempts):
            try:
                response = self._session.request(method, url, headers=headers,
                    allow_redirects=False, timeout=TIMEOUT, **kwargs)
            except Exception:
                if method == 'GET' and attempt + 1 < attempts:
                    self._sleep(2 ** attempt)
                    continue
                raise SourceError('No se pudo conectar con Tandem; la descarga queda pendiente', code='connection_failed') from None
            if response.status_code in (429, 500, 502, 503, 504) and attempt + 1 < attempts:
                retry = response.headers.get('Retry-After', '')
                # Respect a long server pause by stopping, not retrying too early.
                try: delay = float(retry) if retry else 2 ** attempt
                except ValueError: delay = 60
                if delay > 10:
                    raise SourceError('Tandem solicita esperar; vuelva a intentarlo más tarde', response.status_code)
                self._sleep(max(1, delay))
                continue
            if len(response.content) > MAX_BODY:
                raise SourceError('Respuesta demasiado grande; reduzca el periodo de consulta', code='response_too_large')
            return response
        raise SourceError('Descarga no completada')

    @staticmethod
    def _json(response):
        if response.status_code != 200:
            raise SourceError('Tandem rechazó la consulta (HTTP %s)' % response.status_code, response.status_code)
        try:
            value = json.loads(response.content)
        except (ValueError, UnicodeError):
            raise SourceError('Tandem devolvió una respuesta JSON de autenticación no válida', code='auth_schema_changed') from None
        if not isinstance(value, dict):
            raise SourceError('Formato de respuesta de autenticación de Tandem no reconocido', code='auth_schema_changed')
        return value

    def _login(self, email, password):
        self._request('GET', SSO)
        result = self._json(self._request('POST', LOGIN, json={'username': email, 'password': password}))
        if result.get('status') != 'SUCCESS':
            raise SourceError('Acceso no completado; compruebe credenciales o requisitos de acceso', 401)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).decode().rstrip('=')
        state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        url = AUTHORIZE + '?' + urlencode({'client_id': CLIENT_ID, 'response_type': 'code',
            'scope': 'openid profile email', 'redirect_uri': CALLBACK,
            'code_challenge': challenge, 'code_challenge_method': 'S256', 'state': state, 'nonce': nonce})
        code = None
        for _ in range(10):
            parsed = urlsplit(url)
            if parsed.scheme + '://' + parsed.netloc + parsed.path == CALLBACK:
                q = parse_qs(parsed.query)
                if len(q.get('state', [])) != 1 or not hmac.compare_digest(q['state'][0], state):
                    raise SourceError('La verificación de estado de inicio de sesión ha fallado', code='auth_state_mismatch')
                if len(q.get('code', [])) != 1 or q.get('error'):
                    raise SourceError('Tandem requiere intervención para iniciar sesión', 401)
                code = q['code'][0]
                break
            response = self._request('GET', url)
            if response.status_code not in (301, 302, 303, 307, 308) or not response.headers.get('Location'):
                raise SourceError('Acceso pendiente de intervención en Tandem; no se aceptan condiciones automáticamente', 401)
            url = urljoin(url, response.headers['Location'])
        if not code:
            raise SourceError('Inicio de sesión incompleto', 401)
        tokens = self._json(self._request('POST', TOKEN, data={
            'grant_type': 'authorization_code', 'client_id': CLIENT_ID, 'code': code,
            'redirect_uri': CALLBACK, 'code_verifier': verifier}))
        access = tokens.get('access_token')
        if not isinstance(access, str) or not access or tokens.get('token_type', '').lower() != 'bearer':
            raise SourceError('Respuesta de autenticación incompleta', 401, code='token_response_invalid')
        keys = self._json(self._request('GET', JWKS))
        claims = self._verify_id_token(tokens.get('id_token'), keys, nonce, access)
        self.pumper_id = _uuid(claims.get('pumperId'))
        try:
            lifetime = int(tokens['expires_in'])
            if not 0 < lifetime <= 86400: raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise SourceError('Caducidad de sesión no válida', 401, code='token_response_invalid') from None
        self._token = access
        self._expires = time.time() + lifetime

    @staticmethod
    def _verify_id_token(token, keys, nonce, access):
        try:
            import jwt
            from jwt.algorithms import RSAAlgorithm
            header = jwt.get_unverified_header(token)
            if header.get('alg') != 'RS256': raise ValueError()
            matching = [key for key in keys['keys'] if key.get('kid') == header.get('kid')
                        and key.get('kty') == 'RSA' and key.get('use', 'sig') == 'sig'
                        and key.get('alg', 'RS256') == 'RS256' and 'd' not in key]
            if len(matching) != 1: raise ValueError()
            key = RSAAlgorithm.from_jwk(json.dumps(matching[0]))
            claims = jwt.decode(token, key=key, algorithms=['RS256'], audience=CLIENT_ID,
                issuer=ACCOUNTS, leeway=30, options={'require':['exp','iat','sub','aud','iss','nonce']})
            if not hmac.compare_digest(str(claims['nonce']), nonce): raise ValueError()
            aud = claims['aud']
            if isinstance(aud, list) and len(aud) > 1 and claims.get('azp') != CLIENT_ID: raise ValueError()
            if claims.get('azp') and claims['azp'] != CLIENT_ID: raise ValueError()
            if 'at_hash' in claims:
                expected = base64.urlsafe_b64encode(hashlib.sha256(access.encode('ascii')).digest()[:16]).decode().rstrip('=')
                if not hmac.compare_digest(claims['at_hash'], expected): raise ValueError()
            return claims
        except ImportError:
            raise SourceError('Instale PyJWT[crypto] para verificar la identidad de Tandem', code='missing_dependency') from None
        except Exception:
            raise SourceError('La verificación criptográfica de la sesión ha fallado', 401, code='token_verification_failed') from None

    @staticmethod
    def _raw_success(response):
        if response.status_code != 200:
            raise SourceError('Tandem rechazó la consulta (HTTP %s)' % response.status_code, response.status_code)
        return response.content

    def get_pumper(self):
        response = self._request('GET', SOURCE + '/api/reports/bff/pumper/' + self.pumper_id, authorized=True)
        raw = self._raw_success(response)
        self._devices.clear()
        # The collector must archive every HTTP 200 body BEFORE validating its
        # schema. Derive only the device allowlist here; a changed/malformed
        # payload returns unchanged bytes and leaves the allowlist empty.
        try:
            data = json.loads(raw)
            if not isinstance(data, dict) or not isinstance(data.get('pumps'), list):
                return raw
            devices = {_uuid(p['assignmentId']) for p in data['pumps']}
        except (ValueError, UnicodeError, KeyError, TypeError, SourceError):
            return raw
        self._devices = devices
        return raw

    def get_pump_logs(self, device_id, start, end):
        device_id = _uuid(device_id)
        if device_id not in self._devices:
            raise SourceError('Seleccione una bomba de la cuenta consultada', code='unrecognized_device')
        try:
            first, last = date.fromisoformat(str(start)), date.fromisoformat(str(end))
            if not 0 <= (last-first).days < 28: raise ValueError()
        except (ValueError, TypeError):
            raise SourceError('El periodo debe tener de uno a 28 días', code='invalid_period') from None
        # Dates are API selectors, not conversions of device timestamps to UTC.
        query = urlencode({'pumperId':self.pumper_id,'startDate':str(first)+'T00:00:00Z',
                           'endDate':str(last)+'T23:59:59Z'})
        response = self._request('GET', SOURCE+'/api/reports/bff/pump-logs/'+device_id+'?'+query, authorized=True)
        # Validation belongs to the collector, after exact-byte archival.
        return self._raw_success(response)
