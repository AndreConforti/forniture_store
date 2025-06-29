from core.services import fetch_company_data, fetch_address_data
from django.http import JsonResponse
from django.views.decorators.http import require_GET
import logging

logger = logging.getLogger(__name__)

@require_GET
def fetch_company_data_view(request) -> JsonResponse:
    """
    Endpoint Django para buscar dados de uma empresa via CNPJ.

    Espera um parâmetro GET 'tax_id' contendo o CNPJ a ser consultado.
    Delega a busca ao serviço `core.services.fetch_company_data`.
    Retorna uma resposta JSON com os dados da empresa em caso de sucesso,
    ou uma mensagem de erro com o status HTTP apropriado em caso de falha
    (400 para CNPJ ausente/inválido, 500 se o serviço não conseguir obter dados).
    """
    tax_id = request.GET.get('tax_id', '').replace('.', '').replace('-', '').replace('/', '').strip()

    if not tax_id:
        logger.warning("Request received without 'tax_id' parameter.")
        return JsonResponse({'error': 'CNPJ não informado'}, status=400)

    # Validação básica de formato antes de chamar o serviço
    if not tax_id.isdigit() or len(tax_id) not in [11, 14]:
        logger.warning(f"Request received with potentially malformed 'tax_id': {tax_id}")
        return JsonResponse({'error': 'Formato de CNPJ inválido após limpeza. Use apenas números ou formato comum.'}, status=400)


    data = fetch_company_data(tax_id)

    if data:
        logger.info(f"Data fetched successfully for CNPJ {tax_id}")
        return JsonResponse(data)
    else:
        logger.warning(f"Failed to fetch data for CNPJ {tax_id} from services.")
        return JsonResponse({'error': 'Não foi possível obter os dados para o CNPJ fornecido.'}, status=500)

@require_GET
def fetch_address_data_view(request) -> JsonResponse:
    """
    Endpoint Django para buscar dados de endereço via CEP.

    Espera um parâmetro GET 'zip_code' contendo o CEP a ser consultado.
    Delega a busca ao serviço `core.services.fetch_address_data`.
    Retorna uma resposta JSON com os dados do endereço em caso de sucesso,
    ou uma mensagem de erro com o status HTTP apropriado em caso de falha
    (400 para CEP ausente/inválido, 500 se o serviço não conseguir obter dados).
    """
    zip_code = request.GET.get('zip_code', '').strip()

    if not zip_code:
        logger.warning("Request received without 'zip_code' parameter.")
        return JsonResponse({'error': 'CEP não informado'}, status=400)

    # Validação básica de formato antes de chamar o serviço
    cleaned_zip_code = zip_code.replace('-', '')
    if not cleaned_zip_code.isdigit() or len(cleaned_zip_code) != 8:
         logger.warning(f"Request received with potentially malformed 'zip_code': {zip_code}")
         return JsonResponse({'error': 'Formato de CEP inválido após limpeza. Use apenas números ou formato 00000-000.'}, status=400)


    data = fetch_address_data(zip_code)

    if data:
        logger.info(f"Data fetched successfully for CEP {zip_code}")
        return JsonResponse(data)
    else:
        logger.warning(f"Failed to fetch data for CEP {zip_code} from services.")
        return JsonResponse({'error': 'Não foi possível obter os dados para o CEP fornecido.'}, status=500)
