

import base64
import json
import re
from urllib.parse import urlparse, parse_qs, unquote
from typing import Optional, List
from core.server import ServerConfig


class URIParser:
    

    @staticmethod
    def parse(uri: str) -> Optional[ServerConfig]:
        uri = uri.strip()
        if not uri:
            return None

        if uri.startswith("vless://"):
            return URIParser.parse_vless(uri)
        elif uri.startswith("hysteria2://") or uri.startswith("hy2://"):
            return URIParser.parse_hysteria2(uri)

        return None

    @staticmethod
    def parse_vless(uri: str) -> Optional[ServerConfig]:
        try:
            uri = uri.replace("vless://", "", 1)

            name = ""
            if "#" in uri:
                uri, name = uri.rsplit("#", 1)
                name = unquote(name)

            uuid_part, rest = uri.split("@", 1)

            if "?" in rest:
                host_port, params_str = rest.split("?", 1)
            else:
                host_port = rest
                params_str = ""

            if host_port.startswith("["):
                bracket_end = host_port.index("]")
                host = host_port[1:bracket_end]
                port = int(host_port[bracket_end + 2:]) if bracket_end + 2 < len(host_port) else 443
            else:
                parts = host_port.rsplit(":", 1)
                host = parts[0]
                port = int(parts[1]) if len(parts) > 1 else 443

            params = {}
            if params_str:
                for param in params_str.split("&"):
                    if "=" in param:
                        k, v = param.split("=", 1)
                        params[k] = unquote(v)

            server = ServerConfig(
                name=name or f"{host}:{port}",
                server_type="vless",
                address=host,
                port=port,
                uuid=uuid_part,
                encryption=params.get("encryption", "none"),
                flow=params.get("flow", ""),
                transport=params.get("type", "tcp"),
                security=params.get("security", "tls"),
                sni=params.get("sni", ""),
                fingerprint=params.get("fp", "chrome"),
                public_key=params.get("pbk", ""),
                short_id=params.get("sid", ""),
                spider_x=params.get("spx", ""),
                path=params.get("path", ""),
                host=params.get("host", ""),
                service_name=params.get("serviceName", ""),
                alpn=params.get("alpn", ""),
            )

            return server

        except Exception as e:
            print(f"Error parsing VLESS URI: {e}")
            return None

    @staticmethod
    def parse_hysteria2(uri: str) -> Optional[ServerConfig]:
        try:
            uri = re.sub(r'^(hysteria2|hy2)://', '', uri)

            name = ""
            if "#" in uri:
                uri, name = uri.rsplit("#", 1)
                name = unquote(name)

            auth = ""
            if "@" in uri:
                auth, rest = uri.split("@", 1)
            else:
                rest = uri

            if "?" in rest:
                host_port, params_str = rest.split("?", 1)
            else:
                host_port = rest
                params_str = ""

            if host_port.startswith("["):
                bracket_end = host_port.index("]")
                host = host_port[1:bracket_end]
                port_str = host_port[bracket_end + 2:] if bracket_end + 2 < len(host_port) else "443"
                port = int(port_str) if port_str else 443
            else:
                parts = host_port.rsplit(":", 1)
                host = parts[0]
                port = int(parts[1]) if len(parts) > 1 else 443

            params = {}
            if params_str:
                for param in params_str.split("&"):
                    if "=" in param:
                        k, v = param.split("=", 1)
                        params[k] = unquote(v)

            insecure = params.get("insecure", "0") == "1"

            server = ServerConfig(
                name=name or f"{host}:{port}",
                server_type="hysteria2",
                address=host,
                port=port,
                auth=auth,
                sni=params.get("sni", ""),
                obfs=params.get("obfs", ""),
                obfs_password=params.get("obfs-password", ""),
                insecure=insecure,
                fingerprint=params.get("pinSHA256", ""),
            )

            return server

        except Exception as e:
            print(f"Error parsing Hysteria2 URI: {e}")
            return None

    @staticmethod
    def parse_subscription_content(content: str) -> List[ServerConfig]:
        
        servers = []

        decoded = content
        try:
            padding = 4 - len(content.strip()) % 4
            if padding != 4:
                content_padded = content.strip() + "=" * padding
            else:
                content_padded = content.strip()
            decoded = base64.b64decode(content_padded).decode('utf-8')
        except Exception:
            decoded = content

        try:
            data = json.loads(decoded)
            if isinstance(data, dict):
                if 'proxies' in data:
                    for proxy in data['proxies']:
                        server = URIParser._parse_clash_proxy(proxy)
                        if server:
                            servers.append(server)
                    return servers
                elif 'outbounds' in data:
                    for outbound in data['outbounds']:
                        server = URIParser._parse_v2ray_outbound(outbound)
                        if server:
                            servers.append(server)
                    return servers
        except (json.JSONDecodeError, Exception):
            pass

        lines = decoded.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            server = URIParser.parse(line)
            if server:
                servers.append(server)

        return servers

    @staticmethod
    def _parse_clash_proxy(proxy: dict) -> Optional[ServerConfig]:
        try:
            proxy_type = proxy.get('type', '').lower()

            if proxy_type == 'vless':
                server = ServerConfig(
                    name=proxy.get('name', ''),
                    server_type='vless',
                    address=proxy.get('server', ''),
                    port=int(proxy.get('port', 443)),
                    uuid=proxy.get('uuid', ''),
                    flow=proxy.get('flow', ''),
                    transport=proxy.get('network', 'tcp'),
                    security='tls' if proxy.get('tls', False) else 'none',
                    sni=proxy.get('servername', proxy.get('sni', '')),
                    fingerprint=proxy.get('client-fingerprint', 'chrome'),
                )

                reality_opts = proxy.get('reality-opts', {})
                if reality_opts:
                    server.security = 'reality'
                    server.public_key = reality_opts.get('public-key', '')
                    server.short_id = reality_opts.get('short-id', '')

                ws_opts = proxy.get('ws-opts', {})
                if ws_opts:
                    server.path = ws_opts.get('path', '')
                    headers = ws_opts.get('headers', {})
                    server.host = headers.get('Host', '')

                grpc_opts = proxy.get('grpc-opts', {})
                if grpc_opts:
                    server.service_name = grpc_opts.get('grpc-service-name', '')

                return server

            elif proxy_type == 'hysteria2':
                server = ServerConfig(
                    name=proxy.get('name', ''),
                    server_type='hysteria2',
                    address=proxy.get('server', ''),
                    port=int(proxy.get('port', 443)),
                    auth=proxy.get('password', proxy.get('auth-str', '')),
                    sni=proxy.get('sni', ''),
                    insecure=proxy.get('skip-cert-verify', False),
                    obfs=proxy.get('obfs', ''),
                    obfs_password=proxy.get('obfs-password', ''),
                )
                return server

        except Exception as e:
            print(f"Error parsing Clash proxy: {e}")

        return None

    @staticmethod
    def _parse_v2ray_outbound(outbound: dict) -> Optional[ServerConfig]:
        try:
            protocol = outbound.get('protocol', '').lower()
            settings = outbound.get('settings', {})
            stream = outbound.get('streamSettings', {})

            if protocol == 'vless':
                vnext = settings.get('vnext', [{}])[0]
                user = vnext.get('users', [{}])[0]

                server = ServerConfig(
                    name=outbound.get('tag', ''),
                    server_type='vless',
                    address=vnext.get('address', ''),
                    port=int(vnext.get('port', 443)),
                    uuid=user.get('id', ''),
                    flow=user.get('flow', ''),
                    encryption=user.get('encryption', 'none'),
                    transport=stream.get('network', 'tcp'),
                    security=stream.get('security', 'none'),
                )

                tls_settings = stream.get('tlsSettings', {})
                server.sni = tls_settings.get('serverName', '')
                server.fingerprint = tls_settings.get('fingerprint', 'chrome')
                server.alpn = ','.join(tls_settings.get('alpn', []))

                reality = stream.get('realitySettings', {})
                if reality:
                    server.security = 'reality'
                    server.public_key = reality.get('publicKey', '')
                    server.short_id = reality.get('shortId', '')
                    server.sni = reality.get('serverName', server.sni)
                    server.fingerprint = reality.get('fingerprint', server.fingerprint)
                    server.spider_x = reality.get('spiderX', '')

                ws = stream.get('wsSettings', {})
                if ws:
                    server.path = ws.get('path', '')
                    server.host = ws.get('headers', {}).get('Host', '')

                grpc = stream.get('grpcSettings', {})
                if grpc:
                    server.service_name = grpc.get('serviceName', '')

                return server

        except Exception as e:
            print(f"Error parsing V2Ray outbound: {e}")

        return None

    @staticmethod
    def extract_subscription_name(url: str) -> str:
        
        try:
            parsed = urlparse(url)

            query_params = parse_qs(parsed.query)
            for key in ['name', 'remarks', 'tag', 'label', 'title']:
                if key in query_params:
                    val = query_params[key][0]
                    if val:
                        return unquote(val)

            if parsed.fragment:
                return unquote(parsed.fragment)

            path = parsed.path.rstrip('/')
            if path:
                filename = path.split('/')[-1]
                if '.' in filename:
                    filename = filename.rsplit('.', 1)[0]
                if filename and len(filename) > 1:
                    return unquote(filename)

            host = parsed.hostname or ''
            if host:
                host = host.replace('www.', '')
                return host

        except Exception:
            pass

        return "Подписка"