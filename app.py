"""Interface Streamlit para motor V4.8. Execute: streamlit run app.py"""
import json, hashlib, io
from pathlib import Path
from datetime import datetime, timezone
import streamlit as st
from files import v48_reproducible_g3d20 as engine
from v48_caixa_connector import fetch_official
from v48_app_core import verify_frozen

ROOT=Path(__file__).parent
DATA=ROOT/'dados'; DATA.mkdir(exist_ok=True)
P6=ROOT/'files'/'V48_P6_3801_5vs10_FROZEN.json'

st.set_page_config(page_title='Lotofácil V4.8',page_icon='🎯',layout='wide')
st.title('🎯 Lotofácil · V4.8 Reproducible')
st.caption('Protótipo local auditável • motor matemático preservado • sem garantia de ganhos')
st.markdown('''<style>
@media(max-width: 700px) {
  .block-container {padding: 1rem .65rem 3rem !important;}
  .stButton button, .stDownloadButton button {width: 100%; min-height: 44px;}
}
</style>''', unsafe_allow_html=True)

with st.sidebar:
    st.subheader('Configurações')
    cost=st.number_input('Custo por aposta simples (R$)',min_value=0.01,value=3.50,step=0.50)
    budget=st.number_input('Orçamento (R$)',min_value=0.0,value=35.0,step=5.0)
    st.info(f'Com esse orçamento cabem {int(budget//cost)} apostas simples.')
    st.caption('O valor por aposta é configurável; confirme o preço vigente na Caixa.')

def parse_numbers(raw):
    try: ns=[int(x) for x in raw.replace(',',' ').replace(';',' ').replace('-',' ').split()]
    except ValueError: raise ValueError('Use apenas números separados por espaços ou vírgulas.')
    if len(ns)!=15 or len(set(ns))!=15 or any(not 1<=x<=25 for x in ns):
        raise ValueError('São necessárias 15 dezenas distintas de 01 a 25.')
    return sorted(ns)

def audit(games,draw,tiers,cost):
    hits=[len(set(g)&set(draw)) for g in games]
    rows=[{'Jogo':f'{i+1:02d}','Carteira':'Prioritário' if i<5 else 'Complementar','Acertos':h,'Prêmio (R$)':round(float(tiers.get(h,0)),2)} for i,h in enumerate(hits)]
    groups=[]
    for n in (5,10,20):
        if len(games)>=n:
            part=rows[:n]; ret=round(sum(x['Prêmio (R$)'] for x in part),2); stake=round(n*cost,2)
            groups.append({'Carteira':f'{n} jogos','Premiados':sum(x['Prêmio (R$)']>0 for x in part),'Investimento (R$)':stake,'Retorno (R$)':ret,'Saldo (R$)':round(ret-stake,2)})
    return rows,groups

def file_digest(obj):
    return hashlib.sha256(engine.canonical({k:v for k,v in obj.items() if k!='snapshot_sha256'}).encode()).hexdigest()

def load_snap(upload):
    return json.loads(upload.getvalue().decode('utf-8')) if upload else json.loads(P6.read_text(encoding='utf-8'))

tab1,tab2,tab3=st.tabs(['🧮 Gerar e congelar','📋 Conferir jogos','📁 Histórico local'])
with tab1:
    st.subheader('Gerador V4.8 original')
    st.write('A geração usa o código Python original, sem ajuste de pesos ou regras. Para um teste prospectivo, informe somente o resultado oficial do concurso anterior.')
    target=st.number_input('Número do concurso-alvo',min_value=1,value=3802,step=1)
    prev_raw=st.text_input('15 dezenas do concurso anterior (obrigatório)',placeholder='01 02 03 ...')
    count=st.selectbox('Quantidade de jogos',options=[5,10,20],index=1)
    if st.button('Gerar jogos V4.8',type='primary'):
        try:
            prev=parse_numbers(prev_raw)
            full=engine.snapshot(int(target),prev,int(target)-1)
            obj={ 'experiment':f'V4.8 carteira {count}', 'target_contest':int(target),'history_through':int(target)-1,
                'previous_draw':prev,'parent_snapshot_sha256':full['snapshot_sha256'],
                'config_sha256':engine.CONFIG_SHA256,'portfolio':full['portfolio'][:count],
                'status':'FROZEN_BEFORE_RESULT_CHECK','generated_at_utc':datetime.now(timezone.utc).isoformat() }
            obj['snapshot_sha256']=file_digest(obj)
            st.session_state['generated']=obj
        except Exception as exc: st.error(f'Não foi possível gerar: {exc}')
    if 'generated' in st.session_state:
        obj=st.session_state['generated']; games=obj['portfolio']
        st.success(f'{len(games)} jogos gerados. SHA-256: {obj["snapshot_sha256"]}')
        for i,g in enumerate(games): st.write(f'**{i+1:02d} · {"Prioritário" if i<5 else "Complementar"}:** '+ ' · '.join(f'{n:02d}' for n in g))
        st.metric('Custo estimado',f'R$ {len(games)*cost:.2f}')
        if len(games)*cost > budget:
            st.warning('A carteira ultrapassa o orçamento configurado.')
        st.download_button('Baixar snapshot congelado JSON',data=json.dumps(obj,ensure_ascii=False,indent=2),file_name=f'V48_P_{obj["target_contest"]}_{len(games)}_FROZEN.json',mime='application/json')
        if st.button('Salvar no histórico local'):
            p=DATA/f'V48_{obj["target_contest"]}_{len(games)}_{obj["snapshot_sha256"][:12]}.json'
            p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8'); st.success(f'Salvo em {p.name}')
with tab2:
    st.subheader('Auditoria e aferição')
    uploaded=st.file_uploader('Importar snapshot JSON (ou usar P6 de exemplo)',type=['json'])
    try:
        obj=load_snap(uploaded); games=obj['portfolio']
        if obj.get('snapshot_sha256')!=file_digest(obj): raise ValueError('SHA-256 do snapshot não confere: arquivo alterado.')
        if obj.get('config_sha256')!=engine.CONFIG_SHA256: raise ValueError('Configuração incompatível com o motor V4.8.')
        if len(games) not in (5,10,20) or len(set(map(tuple,map(sorted,games))))!=len(games): raise ValueError('Quantidade ou duplicidade inválida.')
        if any(len(g)!=15 or len(set(g))!=15 or any(n<1 or n>25 for n in g) for g in games): raise ValueError('Jogo inválido.')
        st.success(f'Snapshot íntegro · concurso {obj["target_contest"]} · {len(games)} jogos')
        if 'previous_draw' in obj:
            prev=obj['previous_draw']
            parent=engine.snapshot(int(obj['target_contest']),prev,int(obj['target_contest'])-1)
            if parent['snapshot_sha256']!=obj.get('parent_snapshot_sha256') or games!=parent['portfolio'][:len(games)]:
                raise ValueError('Snapshot íntegro, mas não reproduz o motor V4.8.')
            st.success('Reprodução matemática do motor confirmada')
        else: st.warning('Snapshot legado sem dezenas anteriores embutidas: integridade verificada, reprodução matemática não refeita nesta tela.')
        for i,g in enumerate(games): st.write(f'{i+1:02d} · {"Prioritário" if i<5 else "Complementar"} — '+' · '.join(f'{n:02d}' for n in g))
        st.divider()
        official=st.session_state.get('official')
        if official and (official.get('snapshot_sha256') != obj['snapshot_sha256'] or official.get('contest') != obj['target_contest']):
            st.session_state.pop('official', None)
        if st.button(f'Consultar Caixa — concurso {obj["target_contest"]}'):
            try:
                nums,tiers=fetch_official(int(obj['target_contest']))
                st.session_state['official']={'contest':obj['target_contest'],'draw':nums,'tiers':tiers,'source':'CAIXA','snapshot_sha256':obj['snapshot_sha256']}
                st.success('Consulta oficial realizada e validada.')
            except Exception as exc:
                st.session_state.pop('official',None)
                st.error(f'Caixa não confirmada: {exc}. Nenhum resultado foi homologado.')
        official=st.session_state.get('official')
        if official and official['contest']==obj['target_contest'] and official.get('snapshot_sha256')==obj['snapshot_sha256']:
            st.write('**Resultado oficial:** '+' · '.join(f'{n:02d}' for n in sorted(official['draw'])))
            rows,groups=audit(games,official['draw'],official['tiers'],cost)
            st.dataframe(rows,hide_index=True,use_container_width=True)
            st.dataframe(groups,hide_index=True,use_container_width=True)
            report={'contest':obj['target_contest'],'source':'CAIXA','snapshot_sha256':obj['snapshot_sha256'],'draw':official['draw'],'games':rows,'groups':groups}
            st.download_button('Baixar aferição oficial JSON',json.dumps(report,ensure_ascii=False,indent=2),file_name=f'V48_afericao_{obj["target_contest"]}.json')
        else:
            st.info('Aferição oficial pendente. Não serão atribuídos prêmios sem resposta válida da Caixa.')
    except Exception as exc:
        st.session_state.pop('official', None)
        st.error(f'Falha na validação do snapshot: {exc}')
with tab3:
    st.subheader('Snapshots salvos neste computador')
    saved=sorted(DATA.glob('*.json'))
    if not saved: st.info('Ainda não há snapshots salvos. Gere e salve um na primeira aba.')
    for p in saved:
        st.write('📄 '+p.name)
        st.download_button('Exportar',p.read_bytes(),file_name=p.name,key=p.name)
    st.caption('Os arquivos são locais; não existe sincronização em nuvem nesta versão.')
