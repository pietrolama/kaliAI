#!/usr/bin/env python3
"""
Valutazione Qualità RAG - Analisi completa della knowledge base
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge import knowledge_enhancer
import chromadb

class RAGEvaluator:
    """Valuta qualità della RAG system"""
    
    def __init__(self):
        self.enhancer = knowledge_enhancer
        self.test_queries = [
            # Query tecniche
            ("nmap port scanning techniques", "tools"),
            ("SQL injection bypass WAF", "exploits"),
            ("HikVision camera exploit", "exploits"),
            ("CVE-2024 authentication bypass", "cve"),
            ("WiZ smart light UDP control", "exploits"),
            
            # Query tool-specific
            ("curl authentication methods", "tools"),
            ("hydra brute force attack", "tools"),
            ("nikto web vulnerability scanner", "tools"),
            
            # Query generali
            ("IoT device penetration testing", "kb"),
            ("network reconnaissance techniques", "kb"),
            ("web application security", "kb"),
            
            # Query CVE-specific
            ("recent critical vulnerabilities", "cve"),
            ("RCE exploit 2024", "exploits"),
            
            # Query edge cases
            ("non-existent tool xyz123", "none"),  # Dovrebbe restituire poco/niente
            ("", "none"),  # Query vuota
        ]
    
    def get_collection_stats(self) -> Dict:
        """Statistiche dettagliate per collection"""
        stats = {}
        collections = {
            'kali_kb': self.enhancer.kb_collection,
            'full_kb': self.enhancer.full_kb_collection,
            'exploits': self.enhancer.exploits_collection,
            'cve': self.enhancer.cve_collection,
            'successes': self.enhancer.success_collection,
            'tools': self.enhancer.tools_collection
        }
        
        for name, collection in collections.items():
            if collection is None:
                stats[name] = {'count': 0, 'status': 'not_initialized'}
            else:
                count = collection.count()
                stats[name] = {
                    'count': count,
                    'status': 'active' if count > 0 else 'empty'
                }
        
        return stats
    
    def test_query(self, query: str, expected_source: str = None) -> Dict:
        """Testa una query e valuta risultati"""
        if not query.strip():
            return {
                'query': query,
                'results_count': 0,
                'has_results': False,
                'error': 'empty_query'
            }
        
        try:
            results = self.enhancer.enhanced_search(query, top_k=5)
            
            # Analizza risultati
            sources_found = {}
            distances = []
            relevant_count = 0
            
            for res in results:
                source = res.get('source', 'unknown')
                distance = res.get('distance', 1.0)
                
                sources_found[source] = sources_found.get(source, 0) + 1
                distances.append(distance)
                
                # Valuta rilevanza (distance < 0.5 = molto rilevante)
                if distance < 0.5:
                    relevant_count += 1
            
            avg_distance = sum(distances) / len(distances) if distances else 1.0
            min_distance = min(distances) if distances else 1.0
            max_distance = max(distances) if distances else 1.0
            
            # Valuta se ha trovato source atteso
            found_expected = expected_source in sources_found if expected_source else None
            
            # Relevance score: distanza < 0.3 = molto rilevante, < 0.5 = rilevante, > 0.7 = poco rilevante
            # Converti in percentuale (0-100) dove 0.0 distance = 100% relevance
            relevance_score = max(0, (1.0 - avg_distance) * 100)  # 0-100
            
            return {
                'query': query,
                'results_count': len(results),
                'has_results': len(results) > 0,
                'sources_found': sources_found,
                'expected_source': expected_source,
                'found_expected': found_expected,
                'avg_distance': avg_distance,
                'min_distance': min_distance,
                'max_distance': max_distance,
                'relevant_count': relevant_count,
                'relevance_score': relevance_score,
                'results': results[:3]  # Primi 3 per preview
            }
        except Exception as e:
            return {
                'query': query,
                'results_count': 0,
                'has_results': False,
                'error': str(e)
            }
    
    def evaluate_all_queries(self) -> Dict:
        """Valuta tutte le query di test"""
        results = []
        total_queries = len(self.test_queries)
        successful_queries = 0
        relevant_queries = 0
        
        for query, expected_source in self.test_queries:
            result = self.test_query(query, expected_source)
            results.append(result)
            
            if result.get('has_results'):
                successful_queries += 1
                if result.get('relevance_score', 0) > 50:  # >50% relevance
                    relevant_queries += 1
        
        return {
            'total_queries': total_queries,
            'successful_queries': successful_queries,
            'relevant_queries': relevant_queries,
            'success_rate': (successful_queries / total_queries * 100) if total_queries > 0 else 0,
            'relevance_rate': (relevant_queries / total_queries * 100) if total_queries > 0 else 0,
            'results': results
        }
    
    def analyze_coverage(self) -> Dict:
        """Analizza coverage delle collections"""
        stats = self.get_collection_stats()
        total_docs = sum(s['count'] for s in stats.values())
        
        coverage = {}
        for name, stat in stats.items():
            count = stat['count']
            coverage[name] = {
                'count': count,
                'percentage': (count / total_docs * 100) if total_docs > 0 else 0,
                'status': stat['status']
            }
        
        return {
            'total_documents': total_docs,
            'collections': coverage,
            'active_collections': len([s for s in stats.values() if s['count'] > 0])
        }
    
    def test_similarity_quality(self) -> Dict:
        """Testa qualità similarity search con query simili"""
        similar_queries = [
            ("nmap port scan", "nmap scanning ports"),
            ("SQL injection", "SQLi attack"),
            ("authentication bypass", "auth bypass vulnerability"),
        ]
        
        results = []
        for q1, q2 in similar_queries:
            r1 = self.test_query(q1)
            r2 = self.test_query(q2)
            
            # Confronta risultati
            r1_sources = set(r1.get('sources_found', {}).keys())
            r2_sources = set(r2.get('sources_found', {}).keys())
            
            overlap = len(r1_sources & r2_sources)
            similarity_score = (overlap / max(len(r1_sources), len(r2_sources), 1)) * 100
            
            results.append({
                'query1': q1,
                'query2': q2,
                'overlap': overlap,
                'similarity_score': similarity_score
            })
        
        avg_similarity = sum(r['similarity_score'] for r in results) / len(results) if results else 0
        
        return {
            'average_similarity': avg_similarity,
            'tests': results
        }
    
    def generate_report(self) -> str:
        """Genera report completo"""
        print("🔍 VALUTAZIONE QUALITÀ RAG")
        print("=" * 60)
        print()
        
        # 1. Statistiche Collections
        print("📊 STATISTICHE COLLECTIONS")
        print("-" * 60)
        stats = self.get_collection_stats()
        total = sum(s['count'] for s in stats.values())
        print(f"Totale documenti: {total}")
        print()
        for name, stat in stats.items():
            count = stat['count']
            status = stat['status']
            pct = (count / total * 100) if total > 0 else 0
            icon = "✅" if count > 0 else "❌"
            print(f"  {icon} {name:15} {count:6} docs ({pct:5.1f}%) [{status}]")
        print()
        
        # 2. Coverage Analysis
        print("📈 COVERAGE ANALYSIS")
        print("-" * 60)
        coverage = self.analyze_coverage()
        print(f"Collections attive: {coverage['active_collections']}/6")
        print(f"Documenti totali: {coverage['total_documents']}")
        print()
        
        # 3. Query Evaluation
        print("🧪 TEST QUERY")
        print("-" * 60)
        eval_results = self.evaluate_all_queries()
        print(f"Query testate: {eval_results['total_queries']}")
        print(f"Query con risultati: {eval_results['successful_queries']} ({eval_results['success_rate']:.1f}%)")
        print(f"Query rilevanti (>50%): {eval_results['relevant_queries']} ({eval_results['relevance_rate']:.1f}%)")
        print()
        
        # 4. Dettaglio Query
        print("📝 DETTAGLIO QUERY (Top 10)")
        print("-" * 60)
        for i, result in enumerate(eval_results['results'][:10], 1):  # Prime 10
            query = result['query'][:50]
            count = result['results_count']
            score = result.get('relevance_score', 0)
            avg_dist = result.get('avg_distance', 1.0)
            sources = ', '.join(result.get('sources_found', {}).keys())
            
            icon = "✅" if count > 0 else "❌"
            score_icon = "🟢" if score > 50 else "🟡" if score > 30 else "🔴"
            print(f"{i:2}. {icon} {query:50}")
            print(f"    {score_icon} Relevance: {score:.1f}% | Distance: {avg_dist:.3f} | Results: {count}")
            if sources:
                print(f"    📚 Sources: {sources}")
            if result.get('expected_source'):
                found = "✅" if result.get('found_expected') else "❌"
                print(f"    🎯 Expected: {result['expected_source']} {found}")
            print()
        
        # 5. Similarity Quality
        print("🔗 SIMILARITY QUALITY")
        print("-" * 60)
        sim_results = self.test_similarity_quality()
        print(f"Average similarity score: {sim_results['average_similarity']:.1f}%")
        print()
        
        # 6. Raccomandazioni
        print("💡 RACCOMANDAZIONI")
        print("-" * 60)
        
        if coverage['total_documents'] < 1000:
            print("⚠️  Knowledge base piccola (<1000 docs) - considera importare più dati")
        
        if eval_results['success_rate'] < 80:
            print("⚠️  Success rate basso - verifica qualità embeddings")
        
        if eval_results['relevance_rate'] < 60:
            print("⚠️  Relevance rate basso - migliora chunking o embeddings")
            print("    💡 Suggerimento: Verifica che gli embeddings siano corretti")
            print("    💡 Suggerimento: Considera di aumentare chunk_size o migliorare preprocessing")
        
        empty_collections = [name for name, stat in stats.items() if stat['count'] == 0]
        if empty_collections:
            print(f"⚠️  Collections vuote: {', '.join(empty_collections)}")
        
        if coverage['active_collections'] < 3:
            print("⚠️  Poche collections attive - popola più collections")
        
        # 7. Metriche Finali
        print("📊 METRICHE FINALI")
        print("-" * 60)
        print(f"Success Rate:     {eval_results['success_rate']:.1f}%")
        print(f"Relevance Rate:  {eval_results['relevance_rate']:.1f}%")
        print(f"Coverage:        {coverage['active_collections']}/6 collections")
        print(f"Total Docs:      {coverage['total_documents']:,}")
        
        # Calcola score complessivo
        overall_score = (
            eval_results['success_rate'] * 0.4 +
            eval_results['relevance_rate'] * 0.4 +
            (coverage['active_collections'] / 6 * 100) * 0.2
        )
        
        print()
        print(f"🎯 OVERALL SCORE: {overall_score:.1f}/100")
        if overall_score >= 80:
            print("   ✅ Eccellente!")
        elif overall_score >= 60:
            print("   🟡 Buono, ma migliorabile")
        else:
            print("   🔴 Necessita miglioramenti")
        
        print()
        print("=" * 60)
        
        return "Report completato"

def main():
    evaluator = RAGEvaluator()
    evaluator.generate_report()

if __name__ == "__main__":
    main()

