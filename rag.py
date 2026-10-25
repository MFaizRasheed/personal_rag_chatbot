"""Nexus RAG: multi-format document search with a 3D Streamlit workspace."""
import io, os, json
from pathlib import Path
import pandas as pd
import streamlit as st
from openai import APIError, AuthenticationError, OpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

st.set_page_config(page_title="Nexus RAG", page_icon=":material/hub:", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root{--ink:#eaf2ff;--muted:#8ea4c7;--line:rgba(125,166,226,.2);--cyan:#55e6ff}.stApp{background:radial-gradient(circle at 80% 5%,#162d5b,#081122 35%,#050914 75%);color:var(--ink);font-family:'DM Sans',sans-serif}[data-testid="stHeader"]{background:transparent}[data-testid="stSidebar"]{background:rgba(5,12,27,.92);border-right:1px solid var(--line)}[data-testid="stMainBlockContainer"]{max-width:1250px;padding-top:2.2rem}h1,h2,h3{font-family:'Space Grotesk',sans-serif}.muted{color:var(--muted)}.eyebrow{color:var(--cyan);font-size:.76rem;letter-spacing:.2em;text-transform:uppercase;font-weight:700}.hero{padding:1.2rem 0 .5rem}.hero h1{font-size:clamp(2.2rem,5vw,4.5rem);line-height:.98;margin:.5rem 0 1rem;letter-spacing:-.06em}.glass{background:linear-gradient(145deg,rgba(22,42,78,.8),rgba(8,17,35,.72));border:1px solid var(--line);border-radius:22px;padding:1.15rem;box-shadow:0 22px 70px rgba(0,0,0,.24)}.orb-wrap{height:300px;display:grid;place-items:center;perspective:900px;overflow:hidden}.orb{width:190px;height:190px;border-radius:50%;background:radial-gradient(circle at 32% 25%,#d8ffff 0 3%,#55e6ff 8%,#4e5cff 38%,#20104d 72%);box-shadow:0 0 35px #55e6ff,0 0 110px #563cff;animation:float 5s ease-in-out infinite}.orb:before,.orb:after{content:'';position:absolute;inset:-35px;border:1px solid rgba(85,230,255,.7);border-radius:50%;transform:rotateX(68deg) rotateZ(20deg);animation:spin 7s linear infinite}.orb:after{inset:-55px;border-color:rgba(155,140,255,.65);animation-duration:10s}@keyframes spin{to{transform:rotateX(68deg) rotateZ(380deg)}}@keyframes float{50%{transform:translateY(-12px) rotateY(12deg)}}.metric{color:var(--muted);font-size:.8rem}.metric b{display:block;color:var(--ink);font-size:1.5rem;margin-top:.2rem}[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{background:#0d1b35!important;border-color:var(--line)!important;border-radius:12px!important}.stButton button,.stDownloadButton button{border-radius:12px!important;border:1px solid var(--line)!important;background:#102344!important;color:var(--ink)!important}.stButton button:hover{border-color:var(--cyan)!important;color:var(--cyan)!important}.stChatMessage{background:rgba(15,30,56,.55);border:1px solid var(--line);border-radius:16px}
</style>""", unsafe_allow_html=True)

# Keep the workspace hidden until the key is explicitly verified.
if not st.session_state.get("api_verified"):
    gate_left, gate_right = st.columns([1.15, 1], gap="large", vertical_alignment="center")
    with gate_left:
        st.markdown('<div class="eyebrow">Secure workspace / 00</div><div class="hero"><h1>Unlock your<br>knowledge space.</h1><p class="muted">Connect your OpenAI account to activate grounded document search. Your key is kept in this browser session only.</p></div>', unsafe_allow_html=True)
        with st.form("api_gate"):
            # Deliberately do not prefill from environment variables or secrets.
            # A deployed app must ask every browser session for its own key.
            gate_key = st.text_input("OpenAI API key", value="", type="password", placeholder="sk-...")
            verify = st.form_submit_button("Verify and enter workspace", type="primary", width="stretch")
        if verify:
            gate_key = gate_key.strip()
            if not gate_key:
                st.error("Enter an OpenAI API key to continue.")
            else:
                try:
                    OpenAI(api_key=gate_key).models.list()
                    st.session_state.api_key = gate_key
                    st.session_state.api_verified = True
                    st.rerun()
                except AuthenticationError:
                    st.error("That API key was rejected. Check it and try again.")
                except APIError as exc:
                    st.error(f"OpenAI verification failed: {exc}")
                except Exception as exc:
                    st.error(f"Could not verify the key: {exc}")
        st.caption("You can also set OPENAI_API_KEY before launching the app.")
    with gate_right:
        st.markdown('<div class="glass orb-wrap"><div class="orb"></div></div>', unsafe_allow_html=True)
    st.stop()

st.markdown("""<style>
.space-scene{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden}.space-scene i{position:absolute;display:block;opacity:.55;filter:drop-shadow(0 0 12px currentColor)}.diamond{width:18px;height:18px;border:1px solid #55e6ff;transform:rotate(45deg);color:#55e6ff;animation:drift 15s ease-in-out infinite}.ring{width:70px;height:26px;border:1px solid #9b8cff;border-radius:50%;color:#9b8cff;animation:orbit 18s linear infinite}.node{width:9px;height:9px;border-radius:50%;background:#55e6ff;color:#55e6ff;animation:drift 11s ease-in-out infinite}.d1{left:7%;top:18%;animation-delay:-2s}.d2{right:13%;top:68%;animation-delay:-8s}.d3{left:49%;top:9%;animation-delay:-5s}.r1{left:8%;top:72%;animation-delay:-4s}.r2{right:5%;top:22%;animation-delay:-11s}.n1{left:28%;top:22%;animation-delay:-3s}.n2{right:29%;top:37%;animation-delay:-7s}.n3{left:65%;top:83%;animation-delay:-1s}@keyframes drift{0%,100%{transform:translate3d(0,0,0) rotate(45deg)}50%{transform:translate3d(38px,-45px,0) rotate(190deg)}}@keyframes orbit{0%{transform:rotate(-25deg) translateX(0) rotate(0)}50%{transform:rotate(25deg) translateX(65px) rotate(180deg)}100%{transform:rotate(-25deg) translateX(0) rotate(360deg)}}.glass{transition:transform .35s ease,border-color .35s ease}.glass:hover{transform:translateY(-5px);border-color:rgba(85,230,255,.55)}
</style>""",unsafe_allow_html=True)
SUPPORTED=["csv","xlsx","xls","json","docx","pdf"]

def read_file(f):
    name,suffix,raw=f.name,Path(f.name).suffix.lower(),f.getvalue(); meta={"source":name}
    if suffix==".pdf":
        from pypdf import PdfReader
        return [Document(page_content=p.extract_text() or "",metadata={**meta,"page":i+1}) for i,p in enumerate(PdfReader(io.BytesIO(raw)).pages)]
    if suffix in {".csv",".xlsx",".xls"}:
        df=pd.read_csv(io.BytesIO(raw)) if suffix==".csv" else pd.read_excel(io.BytesIO(raw)); return [Document(page_content=df.to_csv(index=False),metadata=meta)]
    if suffix==".json": return [Document(page_content=json.dumps(json.loads(raw.decode()),indent=2),metadata=meta)]
    if suffix==".docx":
        from docx import Document as WordDocument
        d=WordDocument(io.BytesIO(raw)); text="\n".join(p.text for p in d.paragraphs if p.text.strip())
        for table in d.tables: text += "\n"+"\n".join(" | ".join(c.text for c in row.cells) for row in table.rows)
        return [Document(page_content=text,metadata=meta)]
    raise ValueError(f"Unsupported file: {name}")

@st.cache_resource(show_spinner=False)
def make_index(files,size,overlap,api_key):
    docs=[]
    for name,raw in files:
        class Upload: pass
        f=Upload(); f.name=name; f.getvalue=lambda raw=raw:raw; docs.extend(read_file(f))
    chunks=RecursiveCharacterTextSplitter(chunk_size=size,chunk_overlap=overlap).split_documents(docs)
    return FAISS.from_documents(chunks,OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)),len(chunks),len(docs)

def format_docs(docs): return "\n\n".join(f"[{d.metadata.get('source')}{', page '+str(d.metadata['page']) if d.metadata.get('page') else ''}]\n{d.page_content}" for d in docs)
PROMPT=ChatPromptTemplate.from_messages([("system","Answer only from context. If unavailable, say you could not find it. Cite sources like [filename] or [filename, page N].\n\nContext:\n{context}"),("human","{question}")])

with st.sidebar:
    st.markdown("### :material/hub: Nexus RAG"); st.caption("Your private document intelligence space")
    model=st.selectbox("Model",["gpt-4o-mini","gpt-4o","gpt-4.1-mini"]); size=st.slider("Chunk size",500,2000,1000,100); overlap=st.slider("Chunk overlap",0,500,150,50); top_k=st.slider("Sources per answer",2,8,4)
    if st.button("Lock workspace", icon=":material/lock:", width="stretch"):
        for key in ("api_key", "api_verified", "index", "signature", "chunk_count", "doc_count"):
            st.session_state.pop(key, None)
        st.rerun()
    st.divider(); st.caption("Supported formats"); st.markdown("`.pdf`  `.docx`  `.csv`  `.xlsx`  `.xls`  `.json`")
st.markdown('<div class="eyebrow">Document intelligence / 01</div><div class="hero"><h1>Ask your knowledge<br>to come alive.</h1><p class="muted">Drop in your files. Nexus finds the signal, connects the context, and answers with traceable sources.</p></div>',unsafe_allow_html=True)
st.markdown('<div class="space-scene"><i class="diamond d1"></i><i class="diamond d2"></i><i class="diamond d3"></i><i class="ring r1"></i><i class="ring r2"></i><i class="node n1"></i><i class="node n2"></i><i class="node n3"></i></div>',unsafe_allow_html=True)
left,right=st.columns([1.35,1],gap="large")
with right: st.markdown('<div class="glass orb-wrap"><div class="orb"></div></div>',unsafe_allow_html=True)
with left:
    st.markdown('<div class="glass">',unsafe_allow_html=True); uploads=st.file_uploader("Add your knowledge files",type=SUPPORTED,accept_multiple_files=True); st.markdown('</div>',unsafe_allow_html=True)
    if uploads: st.caption(" · ".join(f.name for f in uploads))
api_key=st.session_state.api_key
if uploads:
    signature=tuple((f.name,f.size) for f in uploads)+(size,overlap)
    if st.session_state.get("signature")!=signature:
        with st.spinner("Mapping your knowledge constellation..."): st.session_state.index,st.session_state.chunk_count,st.session_state.doc_count=make_index(tuple((f.name,f.getvalue()) for f in uploads),size,overlap,api_key); st.session_state.signature=signature
        st.success(f"Indexed {len(uploads)} file(s) into {st.session_state.chunk_count} searchable passages.")
if "index" not in st.session_state: st.markdown("### Your workspace is waiting"); st.caption("Upload one or more files above, then ask anything about them below.")
else:
    a,b,c=st.columns(3); a.markdown(f'<div class="metric">FILES<b>{st.session_state.doc_count}</b></div>',unsafe_allow_html=True); b.markdown(f'<div class="metric">PASSAGES<b>{st.session_state.chunk_count}</b></div>',unsafe_allow_html=True); c.markdown('<div class="metric">MODE<b>GROUNDED</b></div>',unsafe_allow_html=True)
    st.markdown("### Explore your documents"); question=st.chat_input("Ask a question about your files...")
    if question:
        retriever=st.session_state.index.as_retriever(search_kwargs={"k":top_k})
        with st.chat_message("user"): st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Retrieving context..."):
                docs=retriever.invoke(question); chain=({"context":lambda _:format_docs(docs),"question":lambda _:question}|PROMPT|ChatOpenAI(model=model,temperature=0,api_key=api_key)|StrOutputParser()); answer=chain.invoke(question)
            st.markdown(answer)
            with st.expander(":material/source: View retrieved sources"):
                for d in docs: st.caption(f"{d.metadata.get('source')}"+(f" · page {d.metadata['page']}" if d.metadata.get("page") else "")); st.text(d.page_content[:600])
