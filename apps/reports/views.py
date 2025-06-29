import pandas as pd
from io import BytesIO, StringIO
from datetime import datetime 
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

from .forms import BaseReportForm, CustomerReportForm, SupplierReportForm

class BaseReportView(LoginRequiredMixin, View):
    # Template pode ser genérico ou cada view define o seu.
    # Se for genérico, precisa ser flexível.
    # Por agora, vamos assumir que cada view define seu template específico.
    template_name = None  # Deve ser definido pela subclasse
    form_class = None     # Deve ser definido pela subclasse
    report_title_default = "Relatório" # Título padrão
    filename_base_default = "relatorio" # Base do nome do arquivo padrão

    def get_report_title(self):
        """Retorna o título do relatório. Pode ser sobrescrito ou usar atributo de classe."""
        return getattr(self, 'report_title', self.report_title_default)

    def get_filename_base(self):
        """Retorna a base do nome do arquivo. Pode ser sobrescrito ou usar atributo de classe."""
        return getattr(self, 'filename_base', self.filename_base_default)

    def get_template_names(self):
        if self.template_name is None:
            raise NotImplementedError("Subclasses de BaseReportView devem definir 'template_name'.")
        return [self.template_name]

    def get_form_class(self):
        if self.form_class is None:
            raise NotImplementedError("Subclasses de BaseReportView devem definir 'form_class'.")
        return self.form_class

    def get(self, request, *args, **kwargs):
        FormClass = self.get_form_class()
        # Preenche o formulário com dados GET se houver, para manter os filtros ao recarregar a página
        form = FormClass(request.GET or None)
        return render(request, self.get_template_names(), {'form': form, 'title': self.get_report_title()})

    def post(self, request, *args, **kwargs):
        FormClass = self.get_form_class()
        form = FormClass(request.POST)

        if form.is_valid():
            queryset = form.get_queryset() # Agora é responsabilidade do Form
            output_format = form.cleaned_data['output_format']
            
            # Prepara os dados brutos (ainda como objetos do modelo ou dicts brutos)
            # A conversão para o formato intermediário de exibição acontece depois
            intermediate_data = self.prepare_intermediate_data_from_queryset(queryset)

            if output_format == 'excel':
                return self.generate_excel(intermediate_data, form)
            elif output_format == 'csv':
                return self.generate_csv(intermediate_data, form)
            elif output_format == 'json':
                return self.generate_json(intermediate_data) # JSON usa intermediate_data diretamente
            else:
                # Esta validação também pode estar no form.cleaned_data['output_format']
                return HttpResponse("Formato de relatório inválido.", status=400)
        else:
            return render(request, self.get_template_names(), {'form': form, 'title': self.get_report_title()})

    def prepare_intermediate_data_from_queryset(self, queryset):
        """
        Converte cada item do queryset para um dicionário de dados intermediários.
        As chaves devem ser técnicas (inglês/snake_case).
        DEVE ser implementado pela subclasse.
        """
        raise NotImplementedError("Subclasses devem implementar prepare_intermediate_data_from_queryset()")

    def get_column_map(self):
        """
        Retorna o mapeamento de chaves técnicas para cabeçalhos de exibição (Português).
        DEVE ser implementado pela subclasse.
        Usado por Excel e CSV.
        Exemplo: {'tech_key': 'Cabeçalho em Português', ...}
        """
        raise NotImplementedError("Subclasses devem implementar get_column_map()")

    def _prepare_dataframe_for_output(self, intermediate_data, column_map):
        """
        Helper para transformar dados intermediários (lista de dicts) em um DataFrame pandas
        com as colunas e cabeçalhos corretos para Excel/CSV.
        """
        output_data_list = []
        # Garante a ordem das colunas de acordo com o column_map
        ordered_headers = list(column_map.values()) 
        
        for item_dict in intermediate_data:
            output_row = {}
            for tech_key, display_header in column_map.items():
                value = item_dict.get(tech_key)
                # O valor já deve estar formatado como string no intermediate_data se necessário (Sim/Não, datas, etc.)
                output_row[display_header] = value if value is not None else '-'
            output_data_list.append(output_row)
        
        # Cria o DataFrame especificando as colunas para manter a ordem
        df = pd.DataFrame(output_data_list)
        if not df.empty and ordered_headers:
             # Reordena colunas e lida com colunas faltantes no DataFrame (preenche com '-')
            df = df.reindex(columns=ordered_headers, fill_value='-')
        elif df.empty and ordered_headers: # DataFrame vazio, mas temos cabeçalhos
            df = pd.DataFrame(columns=ordered_headers)

        return df

    def generate_json(self, intermediate_data):
        """Gera o relatório em formato JSON usando dados intermediários (chaves técnicas)."""
        filename = f'{self.get_filename_base()}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        # O intermediate_data já é uma lista de dicionários com chaves técnicas
        response = JsonResponse(intermediate_data, safe=False, json_dumps_params={'ensure_ascii': False, 'indent': 2})
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def _generate_excel_header_content(self, form):
        """ Gera o conteúdo do cabeçalho para o arquivo Excel. """
        excel_content = []
        excel_content.append([self.get_report_title()])
        excel_content.append([f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'])
        excel_content.append([]) # Linha em branco

        applied_filters_info = form.get_applied_filters_display() # Usa o método do form

        if applied_filters_info:
            excel_content.append(['Filtros Aplicados:'])
            for filter_info in applied_filters_info:
                excel_content.append([filter_info])
        else:
            excel_content.append(['Nenhum filtro aplicado.'])
        excel_content.append([]) # Linha em branco
        return excel_content

    def generate_excel(self, intermediate_data, form):
        """Gera o relatório em formato Excel (xlsx)."""
        column_map = self.get_column_map()
        df_data = self._prepare_dataframe_for_output(intermediate_data, column_map)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            sheet_name = self.get_report_title()[:30] # Limite do Excel para nome de aba

            header_content = self._generate_excel_header_content(form)
            
            current_row = 0
            if header_content:
                df_header = pd.DataFrame(header_content)
                df_header.to_excel(writer, sheet_name=sheet_name, index=False, header=False, startrow=current_row)
                current_row += len(df_header) # Atualiza a linha inicial para os dados

            # Escreve os dados principais (com cabeçalhos das colunas)
            df_data.to_excel(writer, sheet_name=sheet_name, index=False, header=True, startrow=current_row)

            # Opcional: Auto-ajuste da largura das colunas (pode ser lento para muitos dados)
            # worksheet = writer.sheets[sheet_name]
            # for idx, col in enumerate(df_data.columns):  # df_data já tem os cabeçalhos corretos
            #     series = df_data[col]
            #     max_len = max((
            #         series.astype(str).map(len).max(),  # Máximo tamanho do dado
            #         len(str(series.name))  # Tamanho do cabeçalho
            #     )) + 2  # Adiciona um pouco de padding
            #     worksheet.column_dimensions[chr(65+idx)].width = max_len

        excel_value = buffer.getvalue()
        buffer.close()

        filename = f'{self.get_filename_base()}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response = HttpResponse(excel_value, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def generate_csv(self, intermediate_data, form): # Adicionado form para consistência, embora não usado aqui
        """Gera o relatório em formato CSV."""
        column_map = self.get_column_map() # CSV usará o mesmo mapeamento de colunas que o Excel por padrão
        df_data = self._prepare_dataframe_for_output(intermediate_data, column_map)

        buffer = StringIO()
        # Para CSV, geralmente não se coloca o cabeçalho de filtros, apenas os dados.
        # Se quiser, pode adaptar _generate_excel_header_content para gerar strings e prefixá-las com '#'
        df_data.to_csv(buffer, index=False, encoding='utf-8-sig', sep=';', decimal='.')
        csv_value = buffer.getvalue()
        buffer.close()

        filename = f'{self.get_filename_base()}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response = HttpResponse(csv_value, content_type='text/csv; charset=utf-8-sig') # Adicionado charset
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    

class CustomerReportView(BaseReportView):
    template_name = 'reports/customer_report_form.html' # Seu template HTML
    form_class = CustomerReportForm
    report_title = 'Relatório de Clientes'
    filename_base = 'relatorio_clientes'

    def prepare_intermediate_data_from_queryset(self, queryset):
        """
        Prepara os dados do QuerySet de Customer em um formato intermediário (lista de dicionários)
        com chaves técnicas (inglês/snake_case) e valores JÁ FORMATADOS para exibição.
        """
        data = []
        for customer in queryset: # queryset já vem filtrado do form
            address_info = customer.address # Assumindo que o form fez select_related('address')
            address_full_formatted = "-"
            if address_info:
                address_full_formatted = f"{address_info.street or ''}, {address_info.number or 'S/N'}"
                if address_info.complement:
                    address_full_formatted += f" - {address_info.complement}"
                address_full_formatted += f", {address_info.neighborhood or '-'}, {address_info.city or '-'} - {address_info.state or '-'} / CEP: {address_info.formatted_zip_code or '-'}"
            
            # Os valores aqui devem ser strings formatadas para exibição ou None/Booleanos se o JSON precisar deles assim.
            # Para Excel/CSV, strings são melhores.
            data.append({
                'id': customer.pk,
                'customer_type_display': customer.get_customer_type_display(), # Já é string
                'full_name': customer.full_name,
                'preferred_name': customer.preferred_name or '-', # Garante string
                'tax_id_formatted': customer.formatted_tax_id or '-',     # Já é string
                'phone_formatted': customer.formatted_phone or '-',    # Já é string
                'email': customer.email or '-',
                'is_active_display': 'Sim' if customer.is_active else 'Não',
                'is_vip_display': 'Sim' if customer.is_vip else 'Não',
                'profession': customer.profession or '-',
                'interests': customer.interests or '-',
                'notes': customer.notes or '-',
                'registration_date_formatted': customer.registration_date.strftime('%d/%m/%Y %H:%M') if customer.registration_date else '-',
                
                # Campos de endereço (se quiser eles separados também no JSON)
                'address_zip_code_formatted': address_info.formatted_zip_code if address_info else '-',
                'address_street': address_info.street if address_info else '-',
                'address_number': address_info.number if address_info else '-',
                'address_complement': address_info.complement if address_info else '-',
                'address_neighborhood': address_info.neighborhood if address_info else '-',
                'address_city': address_info.city if address_info else '-',
                'address_state': address_info.state if address_info else '-',
                'address_full_formatted': address_full_formatted, # Já formatado acima

                # Se precisar dos valores RAW para o JSON, pode adicioná-los também:
                # 'customer_type_raw': customer.customer_type,
                # 'tax_id_raw': customer.tax_id,
                # 'is_active_raw': customer.is_active,
                # etc.
            })
        return data

    def get_column_map(self):
        """Mapeamento de chaves técnicas para cabeçalhos em Português para Excel/CSV."""
        return {
            'id': 'ID',
            'customer_type_display': 'Tipo',
            'full_name': 'Nome Completo / Razão Social',
            'preferred_name': 'Apelido / Nome Fantasia',
            'tax_id_formatted': 'CPF/CNPJ',
            'phone_formatted': 'Telefone',
            'email': 'E-mail',
            'is_active_display': 'Ativo',
            'is_vip_display': 'VIP',
            'profession': 'Profissão',
            'interests': 'Interesses',
            'notes': 'Observações',
            'registration_date_formatted': 'Data Cadastro',
            # Colunas de endereço separadas no Excel/CSV:
            'address_zip_code_formatted': 'CEP',
            'address_street': 'Logradouro',
            'address_number': 'Número',
            'address_complement': 'Complemento',
            'address_neighborhood': 'Bairro',
            'address_city': 'Cidade',
            'address_state': 'UF',
            'address_full_formatted': 'Endereço Completo',
        }
    

class SupplierReportView(BaseReportView):
    template_name = 'reports/supplier_report_form.html' # Novo template HTML
    form_class = SupplierReportForm
    report_title = 'Relatório de Fornecedores'
    filename_base = 'relatorio_fornecedores'

    def prepare_intermediate_data_from_queryset(self, queryset):
        """
        Prepara os dados do QuerySet de Supplier em um formato intermediário.
        """
        data = []
        for supplier in queryset: # queryset já vem filtrado do form
            address_info = supplier.address
            address_full_formatted = "-"
            if address_info:
                address_full_formatted = f"{address_info.street or ''}, {address_info.number or 'S/N'}"
                if address_info.complement:
                    address_full_formatted += f" - {address_info.complement}"
                address_full_formatted += f", {address_info.neighborhood or '-'}, {address_info.city or '-'} - {address_info.state or '-'} / CEP: {address_info.formatted_zip_code or '-'}"

            data.append({
                'id': supplier.pk,
                'supplier_type_display': supplier.get_supplier_type_display(),
                'full_name': supplier.full_name,
                'preferred_name': supplier.preferred_name or '-',
                'tax_id_formatted': supplier.formatted_tax_id or '-',
                'state_registration': supplier.state_registration or '-',
                'municipal_registration': supplier.municipal_registration or '-',
                'phone_formatted': supplier.formatted_phone or '-',
                'email': supplier.email or '-',
                'contact_person': supplier.contact_person or '-',
                'is_active_display': 'Sim' if supplier.is_active else 'Não',
                'registration_date_formatted': supplier.registration_date.strftime('%d/%m/%Y %H:%M') if supplier.registration_date else '-',
                'bank_name': supplier.bank_name or '-',
                'bank_agency': supplier.bank_agency or '-',
                'bank_account': supplier.bank_account or '-',
                'pix_key': supplier.pix_key or '-',
                'notes': supplier.notes or '-',

                # Campos de endereço
                'address_zip_code_formatted': address_info.formatted_zip_code if address_info else '-',
                'address_street': address_info.street if address_info else '-',
                'address_number': address_info.number if address_info else '-',
                'address_complement': address_info.complement if address_info else '-',
                'address_neighborhood': address_info.neighborhood if address_info else '-',
                'address_city': address_info.city if address_info else '-',
                'address_state': address_info.state if address_info else '-',
                'address_full_formatted': address_full_formatted,
            })
        return data

    def get_column_map(self):
        """Mapeamento de chaves técnicas para cabeçalhos em Português para Excel/CSV."""
        return {
            'id': 'ID',
            'supplier_type_display': 'Tipo',
            'full_name': 'Nome Completo / Razão Social',
            'preferred_name': 'Apelido / Nome Fantasia',
            'tax_id_formatted': 'CPF/CNPJ',
            'state_registration': 'Inscrição Estadual',
            'municipal_registration': 'Inscrição Municipal',
            'phone_formatted': 'Telefone',
            'email': 'E-mail',
            'contact_person': 'Pessoa de Contato',
            'is_active_display': 'Ativo',
            'registration_date_formatted': 'Data Cadastro',
            'bank_name': 'Banco',
            'bank_agency': 'Agência',
            'bank_account': 'Conta',
            'pix_key': 'Chave PIX',
            'notes': 'Observações',
            # Colunas de endereço
            'address_zip_code_formatted': 'CEP',
            'address_street': 'Logradouro',
            'address_number': 'Número',
            'address_complement': 'Complemento',
            'address_neighborhood': 'Bairro',
            'address_city': 'Cidade',
            'address_state': 'UF',
            'address_full_formatted': 'Endereço Completo',
        }
