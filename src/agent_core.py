import datetime
import os
import time
import requests
from Bio import Entrez
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv("config/settings.env")

class PubMedAgent:
    def __init__(self):
        """初始化PubMed智能代理"""
        self.email = os.getenv("ENTREZ_EMAIL")
        self.api_key = os.getenv("ENTREZ_API_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        self.SEARCH_KEYWORD = ""
        
        # 配置Entrez
        Entrez.email = self.email
        if self.api_key:
            Entrez.api_key = self.api_key
        self.request_delay = 0.34  # 遵守NCBI每秒3次的请求限制

    def _get_last_month_dates(self):
        """获取上个月的起止日期"""
        today = datetime.date.today()
        first_day = today.replace(day=1)
        last_month_end = first_day - datetime.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return (
            last_month_start.strftime("%Y/%m/%d"), 
            last_month_end.strftime("%Y/%m/%d")
        )

    def _search_articles(self, keyword, start_date, end_date, max_articles):
        """搜索PubMed文献"""
        search_term = (
            f'({keyword}[Title/Abstract]) AND '
            f'("{start_date}"[PDAT] : "{end_date}"[PDAT]) AND '
            '("free full text"[Filter] OR "open access"[Filter])'
        )
        time.sleep(self.request_delay)
        handle = Entrez.esearch(
            db="pubmed",
            term=search_term,
            retmax=max_articles,
            usehistory="y"
        )
        search_results = Entrez.read(handle)
        return search_results

    def _fetch_article_details(self, webenv, query_key, batch_size=10):
        """批量获取文献详情"""
        time.sleep(self.request_delay)
        handle = Entrez.efetch(
            db="pubmed",
            webenv=webenv,
            query_key=query_key,
            retstart=0,
            retmax=batch_size,
            retmode="xml"
        )
        return Entrez.read(handle)

    def _extract_fulltext(self, article):
        """从文献数据中提取全文"""
        fulltext_data = {
            'type': None,
            'content': None,
            'access': None
        }

        # 尝试获取PMC全文
        if 'ArticleIdList' in article['PubmedData']:
            for id_obj in article['PubmedData']['ArticleIdList']:
                if str(id_obj).startswith('PMC'):
                    try:
                        time.sleep(self.request_delay)
                        handle = Entrez.efetch(
                            db="pmc",
                            id=str(id_obj),
                            retmode="xml"
                        )
                        fulltext_data.update({
                            'type': 'pmc_xml',
                            'content': handle.read(),
                            'access': f"PMC{str(id_obj)}"
                        })
                        break
                    except Exception as e:
                        print(f"PMC全文获取失败: {str(e)}")

        # 尝试获取PDF链接
        if not fulltext_data['type'] and 'PMID' in article['MedlineCitation']:
            pmid = str(article['MedlineCitation']['PMID'])
            pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmid}/pdf/"
            try:
                if requests.head(pdf_url, timeout=5).status_code == 200:
                    fulltext_data.update({
                        'type': 'pdf',
                        'access': pdf_url
                    })
            except:
                pass

        return fulltext_data if fulltext_data['type'] else None

    def _analyze_article(self, title, abstract, fulltext=None):
        """使用DeepSeek API深度分析文章"""
        prompt = f"""作为专业科研助理，请分析这篇论文并回答以下问题：

# 论文标题
{title}

# 摘要
{abstract}

{f"# 全文节选\n{fulltext[:10000]}" if fulltext else ""}

请用中文按以下结构回答：
1. **核心创新点**（列举2-3个最具原创性的贡献）
2. **研究方法**（实验设计或分析方法的独特之处）
3. **潜在局限**（样本量、方法缺陷或未解决的问题）
4. **领域影响**（对该研究领域的推动作用）"""

        headers = {
            "Authorization": f"Bearer {self.deepseek_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=90
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"DeepSeek分析失败: {str(e)}")
            return f"分析未能完成: {str(e)}"

    def _process_article(self, article):
        """处理单篇文献"""
        try:
            medline = article['MedlineCitation']
            article_info = medline['Article']
            journal_info = article_info['Journal']
            
            # 基础元数据
            processed = {
                'pmid': str(medline['PMID']),
                'title': article_info['ArticleTitle'],
                'journal': journal_info['Title'],
                'date': journal_info['JournalIssue']['PubDate'].get('Year', ''),
                'authors': [
                    f"{author.get('LastName', '')} {author.get('Initials', '')}".strip()
                    for author in article_info.get('AuthorList', [])[:5]
                ],
                'abstract': ' '.join(
                    str(t) for t in article_info['Abstract']['AbstractText']
                ) if 'Abstract' in article_info else '无摘要',
                'fulltext': None,
                'analysis': None
            }

            # 获取全文
            processed['fulltext'] = self._extract_fulltext(article)

            # 进行深度分析
            fulltext_content = None
            if processed['fulltext'] and processed['fulltext']['type'] == 'pmc_xml':
                try:
                    root = ET.fromstring(processed['fulltext']['content'])
                    fulltext_content = '\n'.join(
                        ''.join(p.itertext()) 
                        for p in root.findall(".//body//p")[:20]
                    )
                except:
                    pass

            processed['analysis'] = self._analyze_article(
                title=processed['title'],
                abstract=processed['abstract'],
                fulltext=fulltext_content
            )

            return processed

        except Exception as e:
            print(f"文献处理出错: {str(e)}")
            return None

    def _generate_report(self, articles, start_date, end_date):
        """生成完整分析报告"""
        report = [
            f"# PubMed深度分析报告 ({start_date} 至 {end_date})",
            f"**搜索关键词**: {self.SEARCH_KEYWORD}",
            f"**包含文献数**: {len(articles)}篇\n",
            "---\n"
        ]
        
        for idx, article in enumerate(articles, 1):
            if not article:
                continue
                
            section = [
                f"## {idx}. {article['title']}",
                f"- **期刊**: {article['journal']} ({article['date']})",
                f"- **作者**: {', '.join(article['authors'][:3])}{'等' if len(article['authors']) > 3 else ''}",
                f"- **PMID**: {article['pmid']}",
                "\n### 摘要",
                article['abstract']
            ]
            
            # 全文访问信息
            if article['fulltext']:
                section.append("\n### 全文获取")
                if article['fulltext']['type'] == 'pmc_xml':
                    section.append(f"- PMC ID: {article['fulltext']['access']}")
                    section.append(f"- 获取方式: https://www.ncbi.nlm.nih.gov/pmc/articles/{article['fulltext']['access']}")
                else:
                    section.append(f"- PDF链接: {article['fulltext']['access']}")
            
            # 深度分析
            if article['analysis']:
                section.extend([
                    "\n### 深度分析",
                    article['analysis']
                ])
            
            section.append("\n---")
            report.extend(section)
        
        return '\n'.join(report)

    def run(self, keyword, max_articles=5):
        """执行完整分析流程"""
        self.SEARCH_KEYWORD = keyword
        start_date, end_date = self._get_last_month_dates()
        
        try:
            # 第一步：搜索文献
            search_results = self._search_articles(
                keyword, start_date, end_date, max_articles
            )
            count = int(search_results["Count"])
            webenv = search_results["WebEnv"]
            query_key = search_results["QueryKey"]
            
            print(f"找到 {count} 篇相关文献，开始处理前 {max_articles} 篇...")
            
            # 第二步：获取文献详情
            articles_data = self._fetch_article_details(webenv, query_key, max_articles)
            
            # 第三步：处理每篇文献
            processed_articles = []
            for article in articles_data['PubmedArticle']:
                processed = self._process_article(article)
                if processed:
                    processed_articles.append(processed)
                time.sleep(1)  # 控制DeepSeek API调用频率
            
            # 第四步：生成报告
            return self._generate_report(processed_articles, start_date, end_date)
            
        except Exception as e:
            return f"运行过程中出错: {str(e)}"