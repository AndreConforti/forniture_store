## operações externas ou serviços específicos, como chamadas de API, integração com terceiros, envio de notificações, etc.
import requests
import logging

logger = logging.getLogger(__name__)


def fetch_company_data(tax_id: str) -> dict | None:
    """
    Consulta CNPJ em APIs públicas e retorna os dados formatados.

    Este serviço tenta buscar dados de Pessoa Jurídica (Razão Social, Nome Fantasia,
    Endereço, etc.) utilizando o CNPJ fornecido. Ele tenta múltiplos endpoints
    de APIs públicas para aumentar a robustez. O primeiro endpoint que retornar
    dados válidos é utilizado. Os dados são limpos e formatados para um dicionário
    consistente.

    Args:
        tax_id: String contendo o CNPJ a ser consultado (pode incluir formatação).

    Returns:
        Um dicionário com os dados da empresa ('full_name', 'preferred_name',
        'zip_code', 'street', 'number', 'neighborhood', 'city', 'state',
        'state_registration') se a consulta for bem-sucedida e encontrar dados.
        Retorna None se o CNPJ for inválido após limpeza, ou se nenhuma API
        retornar dados válidos após várias tentativas.
    """
    tax_id = tax_id.replace(".", "").replace("-", "").replace("/", "").strip()

    if not tax_id or not tax_id.isdigit() or len(tax_id) != 14:
        logger.warning(f"Tentativa de buscar CNPJ inválido ou vazio: '{tax_id}'")
        return None

    apis = [
        f"https://open.cnpja.com/office/{tax_id}",
        f"https://publica.cnpj.ws/cnpj/{tax_id}",
    ]

    for api_url in apis:
        try:
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()  # Levanta HTTPError para bad responses (4xx ou 5xx)
            data = response.json()

            # Verifica se a API retornou um erro específico (ex: CNPJ not found)
            if data and ("erro" in data or data.get("status") == "ERROR"):
                logger.info(
                    f"API {api_url} retornou erro para CNPJ {tax_id}: {data.get('message') or data.get('error') or data}"
                )
                continue

            if data:
                # Extrai a Inscrição Estadual (IE) ativa ou retorna ""
                state_registration = ""

                # API 1 (open.cnpja.com) - Dados geralmente em chaves 'company', 'address', 'registrations'
                if "company" in data and "address" in data:
                    active_registration = next(
                        (
                            reg
                            for reg in data.get("registrations", [])
                            if reg.get("enabled")
                            and reg.get("type", {}).get("text") == "IE Normal"
                        ),
                        None,
                    )
                    if active_registration:
                        state_registration = active_registration.get("number", "")

                    return {
                        "full_name": (
                            data.get("company", {}).get("name") or ""
                        ).title(),
                        "preferred_name": (data.get("alias") or "").title(),
                        "zip_code": data.get("address", {}).get("zip", ""),
                        "street": (data.get("address", {}).get("street") or "")
                        .title()
                        .strip(),
                        "number": data.get("address", {}).get("number", ""),
                        "neighborhood": (
                            data.get("address", {}).get("district") or ""
                        ).title(),
                        "city": (data.get("address", {}).get("city") or "").title(),
                        "state": data.get("address", {}).get("state", ""),
                        "state_registration": state_registration,
                    }

                # API 2 (publica.cnpj.ws) - Dados geralmente na chave 'estabelecimento'
                elif "estabelecimento" in data:
                    active_registration = next(
                        (
                            ie
                            for ie in data.get("estabelecimento", {}).get(
                                "inscricoes_estaduais", []
                            )
                            if ie.get("ativo")
                        ),
                        None,
                    )
                    if active_registration:
                        state_registration = active_registration.get(
                            "inscricao_estadual", ""
                        )

                    return {
                        "full_name": (data.get("razao_social", "")).title(),
                        "preferred_name": (
                            data.get("estabelecimento", {}).get("nome_fantasia", "")
                        ).title(),
                        "zip_code": data.get("estabelecimento", {}).get("cep", ""),
                        "street": (
                            f"{data.get('estabelecimento', {}).get('tipo_logradouro', '')} {data.get('estabelecimento', {}).get('logradouro', '')}"
                        )
                        .title()
                        .strip(),
                        "number": data.get("estabelecimento", {}).get("numero", ""),
                        "neighborhood": (
                            data.get("estabelecimento", {}).get("bairro", "")
                        ).title(),
                        "city": (
                            data.get("estabelecimento", {})
                            .get("cidade", {})
                            .get("nome", "")
                        ).title(),
                        "state": data.get("estabelecimento", {})
                        .get("estado", {})
                        .get("sigla", ""),
                        "state_registration": state_registration,
                    }

        except requests.RequestException as e:
            logger.error(f"Erro ao consultar API {api_url} para CNPJ {tax_id}: {e}")
        except Exception as e:
            logger.error(
                f"Erro inesperado ao processar resposta da API {api_url} para CNPJ {tax_id}: {e}"
            )

    logger.warning(f"Não foi possível obter dados para o CNPJ {tax_id} de nenhuma API.")
    return None


def fetch_address_data(zip_code: str) -> dict | None:
    """
    Consulta CEP em APIs públicas e retorna os dados formatados.

    Este serviço tenta buscar dados de endereço (Logradouro, Bairro, Cidade, UF)
    utilizando o CEP fornecido. Ele tenta múltiplos endpoints de APIs públicas
    para aumentar a robustez. O primeiro endpoint que retornar dados válidos é
    utilizado. Os dados são limpos e formatados para um dicionário consistente.

    Args:
        zip_code: String contendo o CEP a ser consultado (pode incluir formatação).

    Returns:
        Um dicionário com os dados do endereço ('zip_code', 'street',
        'neighborhood', 'city', 'state') se a consulta for bem-sucedida e
        encontrar dados. Retorna None se o CEP for inválido após limpeza,
        ou se nenhuma API retornar dados válidos após várias tentativas.
    """
    zip_code = zip_code.replace("-", "").strip()

    if not zip_code or not zip_code.isdigit() or len(zip_code) != 8:
        logger.warning(f"Tentativa de buscar CEP inválido ou vazio: '{zip_code}'")
        return None

    apis = [
        f"https://viacep.com.br/ws/{zip_code}/json/",
        f"https://brasilapi.com.br/api/cep/v1/{zip_code}",
    ]

    for api_url in apis:
        try:
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()  # Levanta HTTPError para bad responses (4xx ou 5xx)
            data = response.json()

            # Verifica se a API retornou um erro específico (ex: CEP not found)
            if data and ("erro" in data or data.get("status") == "ERROR"):
                logger.info(
                    f"API {api_url} retornou erro para CEP {zip_code}: {data.get('message') or data.get('error') or data}"
                )
                continue
            if (
                data and "cep" in data
            ):  # ViaCEP usa "cep", BrasilAPI usa "cep" também, mas a presença garante dado
                return {
                    "zip_code": zip_code,
                    "street": data.get("logradouro", "") or data.get("street", ""),
                    "neighborhood": data.get("bairro", "")
                    or data.get("neighborhood", ""),
                    "city": data.get("localidade", "") or data.get("city", ""),
                    "state": data.get("uf", "") or data.get("state", ""),
                }

        except requests.RequestException as e:
            logger.error(f"Erro ao consultar API {api_url} para CEP {zip_code}: {e}")
        except Exception as e:
            logger.error(
                f"Erro inesperado ao processar resposta da API {api_url} para CEP {zip_code}: {e}"
            )

    logger.warning(
        f"Não foi possível obter dados para o CEP {zip_code} de nenhuma API."
    )
    return None
