# Forniture Store - Sistema de Gestão Integrada (ERP/CRM)

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12+-yellow.svg)
![Django](https://img.shields.io/badge/Django-5.2+-green.svg)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue.svg)

## 📖 Visão Geral do Projeto

Este projeto é um sistema de gestão integrado (ERP/CRM) desenvolvido em Django para atender às necessidades de uma loja de móveis e decoração, a **"Forniture Store"**. O objetivo principal é centralizar e otimizar as operações diárias, desde o cadastro e relacionamento com clientes e fornecedores até a geração de relatórios gerenciais.

O sistema está sendo construído modularmente, permitindo uma implementação e um deploy faseado das funcionalidades. Atualmente, os módulos de **Clientes, Fornecedores e Relatórios** estão implementados e funcionais.

**[➡️ Link para a Demonstração Ao Vivo]** (Será adicionado o link aqui quando for finalizado o deploy)

---

## ✨ Funcionalidades Implementadas

### 👤 **Gestão de Clientes e Fornecedores**
- **CRUD Completo:** Criação, Leitura, Atualização e Exclusão de registros para Clientes e Fornecedores.
- **Tipos de Entidade:** Suporte para Pessoas Físicas (PF) e Pessoas Jurídicas (PJ), com formulários que se adaptam dinamicamente aos campos necessários.
- **Validação de Documentos:** Validação em tempo real para CPF e CNPJ (utilizando `validate-docbr`), garantindo a integridade dos dados fiscais.
- **Busca e Filtragem:** Ferramentas de busca e filtros avançados nas listagens para encontrar registros por nome, documento, e-mail e tipo.

### 🔌 **Integração com APIs Externas**
- **Busca por CNPJ:** Preenchimento automático de Razão Social, Nome Fantasia e Endereço ao digitar um CNPJ válido para um cliente ou fornecedor, consultando uma API externa.
- **Busca por CEP:** Preenchimento automático de Logradouro, Bairro, Cidade e UF ao informar um CEP, agilizando o cadastro de endereços para qualquer entidade.
- **Cache de API:** Os resultados das consultas de CEP são armazenados em cache para otimizar o desempenho e reduzir requisições repetidas.

### 📊 **Módulo de Relatórios Avançado**
- **Relatórios de Clientes e Fornecedores:** Telas dedicadas para gerar relatórios detalhados.
- **Filtros Dinâmicos:** Formulários permitem a combinação de múltiplos filtros (nome, tipo, status, cidade, estado, etc.) para extrair dados precisos.
- **Exportação Multiformato:** Geração de relatórios nos formatos **Excel (.xlsx)**, **CSV (.csv)** e **JSON (.json)**.
- **Processamento com Pandas:** Utilização da biblioteca `pandas` para manipulação eficiente dos dados e geração dos arquivos, garantindo performance e flexibilidade.

### 🏛️ **Arquitetura e Design**
- **Modelo de Endereço Genérico:** Um modelo `Address` centralizado com `GenericForeignKey` permite que qualquer outra entidade do sistema (Clientes, Fornecedores, etc.) possa ter um endereço sem duplicação de código.
- **Código Modular:** O projeto é organizado em apps Django com responsabilidades bem definidas (`addresses`, `customers`, `suppliers`, `reports`, `docs`), facilitando a manutenção e a escalabilidade.
- **Serviços Desacoplados:** A lógica de comunicação com APIs externas está isolada em `core/services`, separando as preocupações e mantendo os modelos limpos.

### 📚 **Documentação Integrada**
- Um app `docs` dedicado serve como um manual do usuário dentro do próprio sistema, explicando passo a passo como utilizar cada funcionalidade implementada.

---

## 📸 Screenshots

| Tela de Listagem de Clientes | Formulário de Cadastro (com busca de CNPJ) |
| :-------------------------: | :--------------------------: |
| *Adicione um screenshot aqui* | *Adicione um screenshot aqui* |

| Formulário de Relatório de Clientes | Documentação Integrada |
| :-------------------------: | :--------------------------: |
| *Adicione um screenshot aqui* | *Adicione um screenshot aqui* |

*(**Dica:** Substitua o texto "Adicione um screenshot aqui" pela imagem real. Você pode arrastar e soltar a imagem na caixa de edição do GitHub para fazer o upload e obter o link.)*

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python, Django
- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
- **Banco de Dados:** PostgreSQL
- **Manipulação de Dados:** Pandas
- **Validação de Documentos:** validate-docbr
- **Servidor (Produção):** Gunicorn, WhiteNoise
- **Variáveis de Ambiente:** python-dotenv

---

