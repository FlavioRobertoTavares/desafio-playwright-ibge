# Autor: Flávio Roberto Tavares Bezerra
# OBS: Como somente eu estava desenvolvendo, resolvi fazer tudo localmente, no lugar de fazer pequenos commits ao github
from playwright.sync_api import sync_playwright
import pandas as pd # IMPORTANTE: Não foi usado no desenvolvimento da solução, apenas para exportar a planilha

# Dicionário que guardará os dados extraidos
complete_data = {}

# Link do site dado pelo desafio
IBGE = "https://cidades.ibge.gov.br/"

# Como os dados de "Saúde" e "Meio Ambiente" não se encontravam na página individual de cada estado, tive que pegar do seus resumos de municipios, será explicado mais a frente
health = ['Estabelecimentos de Saúde SUS [2009]', 'Mortalidade Infantil [2022]', 'Internações por diarreia pelo SUS [2022]']
environment = ['Urbanização de vias públicas [2010]', 'Arborização de vias públicas [2010]', 'Esgotamento sanitário adequado [2010]', 'População exposta ao risco [2010]', 'Área urbanizada [2019]']

# Recebe uma lista com dados sem formatação e os formata, além de classificá los por tipo, então os retorna
def clear_data(list, types):
    data = {}
    data_type = ''
    for item in list:
            
        item = item.replace('\xa0', '')
            
        lines = [line.strip() for line in item.split('\n') if line.strip()]

        string = ' '.join(lines)
        
        if string in types:
            data_type = string
            data[data_type] = []

        elif string != '': 
            data[data_type].append(string)
                
    return data

# Uma função que seleciona os dados que queremos pegar do resumo, recebe a pagina e o nome dos dados e faz a ação (usada para Saúde e Meio Ambiente)
def resumo_click(page, infos):
    for info in infos:
        page.get_by_label(info).click()

# A função que efetivamente pega os dados do resumo de Saúde e Meio Ambiente. Ela seleciona as informações, vai ao pop-up delas, as coleta, generealiza e então fecha o pop-up
# Recebe a pagina, informações desejadas e tipo de dados(Saúde ou Meio Ambiente), retorna os dados formatados e generealizados para o estado
def get_from_summary(page, infos, type):
    partial_data = []

    resumo_click(page, infos)

    with page.expect_popup() as popup:
        page.locator('div.modal_resumo_content > button').click()

    popup_page = popup.value
    popup_page.wait_for_load_state('networkidle')
    
    for i in range(3, 3 + len(infos)):
        if i == 3 and type == 'health': 
            mean = False
        
        else:
            mean = True

        list = popup_page.locator(f'#municipios > tbody > tr > td:nth-child({i})').all_inner_texts()
        if len(list) > 0:
            partial_data.append(infos[i-3] + " " + total_info(list, mean))
    
    popup_page.close()

    popup_page.is_closed()

    resumo_click(page, infos)

    return partial_data

# A função de abrir o menu onde estão todos os estados, coloquei numa função para evitar repetições de código
def open_state_menu(page):
    page.locator('#abaMenuLateral').click()
    page.locator('#menu__estado').click()

# Função que vai generealizar os dados de Saúde e Meio Ambiente dos municipios para estados
def total_info(list, mean):
    total_sum = 0
    text = ''
    
    for element in list:
        element = element.strip()
        if element in ['-', 'Sem dados pessoas', 'Não pertence']: 
            continue

        element = element.split(' ', 1)

        text = element[1]
        number = element[0]
        number = float(number.replace(',', '.'))
        total_sum += number

    if mean: 
        total_sum = total_sum / len(list)
    else:
        total_sum = int(total_sum)

    return str(total_sum)[:6] + ' ' + text


with sync_playwright() as play:
    browser = play.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(IBGE)

    open_state_menu(page)
    
    # Pega o nome dos estados brasileiros de forma automatica
    states = page.locator('#segunda-coluna > ul').all_inner_texts()
    states = states[0].split("\n")

    # Extraí informações de cada estado
    for state in states: 
        print(state)
        state_url = page.locator(f"//a[normalize-space(.)='{state}']").get_attribute('href')

        page.goto(IBGE+state_url)
        page.wait_for_load_state('networkidle')

        # Pega os tipos de dados disponiveis para aquele estado, no geral: População, Educação, Trabalho e Rendimento, Economia e Territorio
        types = page.locator('th.lista__titulo').all_inner_texts()

        # Pega os dados de cada tipo e então os limpa e formata
        partial_data = page.locator('#dados > panorama-resumo > div > table > tr').all_inner_texts()
        complete_data[state] = clear_data(partial_data, types)

        # Abre o menu de resumo para pegar os dados do tipo Saúde e Meio Ambiente, que só estão disponiveis pelos municipios
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.locator('div.fontes-e-nota-geral', has_text='Gerar Resumo').click()

        # Pega as informações, as limpam, formatam e generealizam
        complete_data[state]['SAÚDE'] = get_from_summary(page, health, 'health')
        complete_data[state]['MEIO AMBIENTE'] = get_from_summary(page, environment, 'environment')

        page.goto(IBGE)
        page.wait_for_load_state("networkidle")

        open_state_menu(page)

    print('\n----------- Finalizado, resultados: -------------------\n')

    # Um print de como fica o dicionário com todas as informações antes de ir pro Excel
    print(complete_data)
    browser.close()

#-------------------- APENAS PARA EXPORTAR PLANILHA, NÃO USADO NA EXTRAÇÃO DE INFORMAÇÕES --------------------
excel_data = []

for state, types in complete_data.items():
    for type, item in types.items():
        if not item:
            excel_data.append({
                'Estado': state,
                'Tipo do Dado': type,
                'Conteúdo do Dado': None
            })
        else:
            for item in item:
                excel_data.append({
                    'Estado': state,
                    'Tipo do Dado': type,
                    'Conteúdo do Dado': item
                })

df = pd.DataFrame(excel_data)
excel_name = 'Brazilian_states_data.xlsx'
df.to_excel(excel_name, index=False, engine='openpyxl')

print(f"\n\nPlanilha '{excel_name}' criada com sucesso!\n")