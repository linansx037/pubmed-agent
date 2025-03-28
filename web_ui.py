import streamlit as st
from src.agent_core import PubMedAgent

def main():
    st.title("PubMed智能文献分析系统")
    
    with st.sidebar:
        st.header("配置参数")
        keyword = st.text_input("搜索关键词", "neurodegenerative diseases")
        max_articles = st.slider("最大文献数", 1, 20, 5)
        email = st.text_input("联系邮箱", "your_email@domain.com")
    
    if st.button("开始分析"):
        agent = PubMedAgent()
        agent.email = email
        
        with st.spinner("正在搜索文献..."):
            report = agent.run(keyword, max_articles)
            
        st.download_button(
            label="下载报告",
            data=report,
            file_name=f"pubmed_report_{datetime.datetime.now().strftime('%Y%m%d')}.md"
        )
        st.success("分析完成！")

if __name__ == "__main__":
    main()