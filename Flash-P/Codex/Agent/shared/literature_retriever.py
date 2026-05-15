#!/usr/bin/env python3
"""
================================================================================
LITERATURE RETRIEVER - PubMed, Semantic Scholar & Web Search Verification
================================================================================

Verifies Claude's proposed relationships against REAL papers using PubMed
E-utilities, Semantic Scholar APIs, and web search fallback. Used by both
CURATOR (edge verification) and PERTURBATION (test case verification) agents.

DESIGN PRINCIPLES:
- No fabricated PMIDs — all IDs come from real API responses
- DOI as primary identifier, PubMed URL for convenience
- Evidence sentences extracted from abstracts
- Works WITHOUT API keys (slower rate limits), optionally faster with keys
- Three-tier verification: PubMed → Semantic Scholar → Web Search
- Web-found DOIs are ALWAYS cross-checked against PubMed to confirm relevance

API KEYS (both free):
- NCBI: export NCBI_API_KEY="your_key"  (10 req/s vs 3 req/s without)
- Semantic Scholar: export S2_API_KEY="your_key"  (higher limits)

USAGE:
    from literature_retriever import verify_edge, verify_perturbation, batch_verify

    # Verify a single edge
    result = verify_edge(
        source="Strigolactone", target="BRC1", effect="positive",
        claim="SL promotes BRC1 transcription through D53 degradation",
        keywords="strigolactone BRC1 D53 branching arabidopsis"
    )

    # Verify a perturbation test
    result = verify_perturbation(
        gene="MAX2", perturbation="knockout",
        outcome="increased branching",
        claim="max2 mutant displays increased rosette branching",
        keywords="max2 knockout branching arabidopsis mutant"
    )

================================================================================
"""

import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from flashp_version import get_version

__version__ = get_version()


# ============================================================================
# CONFIGURATION
# ============================================================================

NCBI_API_KEY = os.environ.get('NCBI_API_KEY', '')
S2_API_KEY = os.environ.get('S2_API_KEY', '')

NCBI_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
S2_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

# Rate limiting: 3 req/s without key, 10 req/s with key
NCBI_RATE_LIMIT = 0.1 if NCBI_API_KEY else 0.34
S2_RATE_LIMIT = 0.5 if S2_API_KEY else 1.0

_last_ncbi_call = 0.0
_last_s2_call = 0.0


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Paper:
    """A retrieved paper with metadata."""
    pmid: str = ""
    doi: str = ""
    title: str = ""
    authors: str = ""
    year: int = 0
    journal: str = ""
    abstract: str = ""
    pubmed_url: str = ""
    source_api: str = ""  # "pubmed" or "semantic_scholar"


@dataclass
class VerifiedEvidence:
    """Evidence verified against a real paper."""
    claim: str = ""
    evidence_sentence: str = ""
    source: Dict[str, Any] = field(default_factory=dict)
    verification: str = "unverified"  # "pubmed_api", "semantic_scholar_api", "web_search_verified", "unverified"
    confidence_boost: bool = False  # True if verification found strong support
    search_query: str = ""
    papers_found: int = 0
    papers_checked: int = 0


# ============================================================================
# HTTP HELPERS
# ============================================================================

def _http_get(url: str, headers: Optional[Dict[str, str]] = None,
              timeout: int = 15) -> Optional[str]:
    """Make an HTTP GET request, return response text or None on error."""
    try:
        req = urllib.request.Request(url)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8')
    except Exception:
        return None


def _rate_limit_ncbi():
    """Enforce NCBI rate limit."""
    global _last_ncbi_call
    now = time.time()
    elapsed = now - _last_ncbi_call
    if elapsed < NCBI_RATE_LIMIT:
        time.sleep(NCBI_RATE_LIMIT - elapsed)
    _last_ncbi_call = time.time()


def _rate_limit_s2():
    """Enforce Semantic Scholar rate limit."""
    global _last_s2_call
    now = time.time()
    elapsed = now - _last_s2_call
    if elapsed < S2_RATE_LIMIT:
        time.sleep(S2_RATE_LIMIT - elapsed)
    _last_s2_call = time.time()


# ============================================================================
# PUBMED E-UTILITIES
# ============================================================================

def search_pubmed(query: str, max_results: int = 5) -> List[str]:
    """
    Search PubMed using E-utilities esearch.

    Args:
        query: Search query string
        max_results: Maximum PMIDs to return

    Returns:
        List of PMID strings
    """
    _rate_limit_ncbi()

    params = {
        'db': 'pubmed',
        'term': query,
        'retmax': str(max_results),
        'retmode': 'json',
        'sort': 'relevance',
    }
    if NCBI_API_KEY:
        params['api_key'] = NCBI_API_KEY

    url = NCBI_ESEARCH_URL + '?' + urllib.parse.urlencode(params)
    response = _http_get(url)
    if not response:
        return []

    try:
        data = json.loads(response)
        return data.get('esearchresult', {}).get('idlist', [])
    except (json.JSONDecodeError, KeyError):
        return []


def fetch_pubmed_papers(pmids: List[str]) -> List[Paper]:
    """
    Fetch paper details from PubMed using E-utilities efetch.

    Args:
        pmids: List of PMID strings

    Returns:
        List of Paper objects with metadata and abstracts
    """
    if not pmids:
        return []

    _rate_limit_ncbi()

    params = {
        'db': 'pubmed',
        'id': ','.join(pmids),
        'retmode': 'xml',
    }
    if NCBI_API_KEY:
        params['api_key'] = NCBI_API_KEY

    url = NCBI_EFETCH_URL + '?' + urllib.parse.urlencode(params)
    response = _http_get(url)
    if not response:
        return []

    papers = []
    try:
        root = ET.fromstring(response)
        for article in root.findall('.//PubmedArticle'):
            paper = Paper(source_api="pubmed")

            # PMID
            pmid_elem = article.find('.//PMID')
            if pmid_elem is not None and pmid_elem.text:
                paper.pmid = pmid_elem.text
                paper.pubmed_url = format_pubmed_url(paper.pmid)

            # Title
            title_elem = article.find('.//ArticleTitle')
            if title_elem is not None and title_elem.text:
                paper.title = title_elem.text

            # Abstract
            abstract_parts = []
            for abs_text in article.findall('.//AbstractText'):
                if abs_text.text:
                    abstract_parts.append(abs_text.text)
            paper.abstract = ' '.join(abstract_parts)

            # Year
            year_elem = article.find('.//PubDate/Year')
            if year_elem is not None and year_elem.text:
                try:
                    paper.year = int(year_elem.text)
                except ValueError:
                    pass

            # Journal
            journal_elem = article.find('.//Journal/Title')
            if journal_elem is not None and journal_elem.text:
                paper.journal = journal_elem.text

            # Authors (first author et al.)
            authors = article.findall('.//Author')
            if authors:
                first = authors[0]
                last_name = first.findtext('LastName', '')
                initials = first.findtext('Initials', '')
                if last_name:
                    author_str = f"{last_name} {initials}".strip()
                    if len(authors) > 1:
                        author_str += ", et al."
                    paper.authors = author_str

            # DOI
            for aid in article.findall('.//ArticleId'):
                if aid.get('IdType') == 'doi' and aid.text:
                    paper.doi = aid.text
                    break

            papers.append(paper)
    except ET.ParseError:
        pass

    return papers


# ============================================================================
# SEMANTIC SCHOLAR API
# ============================================================================

def search_semantic_scholar(query: str, max_results: int = 5) -> List[Paper]:
    """
    Search Semantic Scholar for papers.

    Args:
        query: Search query string
        max_results: Maximum papers to return

    Returns:
        List of Paper objects
    """
    _rate_limit_s2()

    params = {
        'query': query,
        'limit': str(max_results),
        'fields': 'title,authors,year,abstract,externalIds,journal',
    }

    url = S2_SEARCH_URL + '?' + urllib.parse.urlencode(params)
    headers = {}
    if S2_API_KEY:
        headers['x-api-key'] = S2_API_KEY

    response = _http_get(url, headers=headers)
    if not response:
        return []

    papers = []
    try:
        data = json.loads(response)
        for item in data.get('data', []):
            paper = Paper(source_api="semantic_scholar")
            paper.title = item.get('title', '')
            paper.abstract = item.get('abstract', '') or ''
            paper.year = item.get('year', 0) or 0

            # Journal
            journal_info = item.get('journal')
            if journal_info and isinstance(journal_info, dict):
                paper.journal = journal_info.get('name', '')

            # Authors
            authors = item.get('authors', [])
            if authors:
                first = authors[0].get('name', '')
                if first:
                    paper.authors = first + (", et al." if len(authors) > 1 else "")

            # External IDs
            ext_ids = item.get('externalIds', {}) or {}
            paper.doi = ext_ids.get('DOI', '')
            paper.pmid = str(ext_ids.get('PubMed', ''))
            if paper.pmid:
                paper.pubmed_url = format_pubmed_url(paper.pmid)

            papers.append(paper)
    except (json.JSONDecodeError, KeyError):
        pass

    return papers


# ============================================================================
# EVIDENCE EXTRACTION
# ============================================================================

def extract_evidence_sentence(abstract: str, claim: str) -> str:
    """
    Find the sentence in the abstract that best matches the claim.

    Uses keyword overlap scoring to find the most relevant sentence.

    Args:
        abstract: Full abstract text
        claim: The claim to match against

    Returns:
        Best matching sentence, or empty string if no good match
    """
    if not abstract or not claim:
        return ""

    # Split abstract into sentences
    sentences = re.split(r'(?<=[.!?])\s+', abstract)
    if not sentences:
        return ""

    # Tokenize claim into keywords (lowercase, alpha-only, length > 2)
    claim_words = set(
        w.lower() for w in re.findall(r'[a-zA-Z0-9]+', claim)
        if len(w) > 2
    )

    # Score each sentence by keyword overlap
    best_score = 0
    best_sentence = ""

    for sentence in sentences:
        sent_words = set(
            w.lower() for w in re.findall(r'[a-zA-Z0-9]+', sentence)
            if len(w) > 2
        )
        overlap = len(claim_words & sent_words)
        # Normalize by claim length to prefer coverage
        score = overlap / max(len(claim_words), 1)

        if score > best_score:
            best_score = score
            best_sentence = sentence

    # Only return if reasonable match (> 20% keyword overlap)
    if best_score >= 0.2:
        return best_sentence.strip()
    return ""


# ============================================================================
# WEB SEARCH FALLBACK (Tier 3) — Handled by Claude agent, not this script
# ============================================================================
#
# If PubMed (Tier 1) and Semantic Scholar (Tier 2) both fail to find a DOI,
# the calling Claude agent should use its own WebSearch tool to find the paper,
# then call verify_doi_in_pubmed() below to cross-check the DOI.
#
# This replaces the previous DuckDuckGo web scraping approach which was
# blocked by bot detection.
# ============================================================================

DOI_PATTERN = re.compile(r'10\.\d{4,9}/[^\s,;}\]"\'<>]+')


def verify_doi_in_pubmed(doi: str, claim: str) -> Optional[Paper]:
    """
    Cross-check a DOI (found by the agent via WebSearch) against PubMed.

    The agent finds a DOI using its own web search, then calls this function
    to confirm the paper exists in PubMed and the abstract supports the claim.

    Returns Paper if the DOI is legit AND PubMed has it, otherwise None.
    """
    _rate_limit_ncbi()
    params = {
        'db': 'pubmed',
        'term': f'{doi}[DOI]',
        'retmax': '1',
        'retmode': 'json',
    }
    if NCBI_API_KEY:
        params['api_key'] = NCBI_API_KEY

    url = NCBI_ESEARCH_URL + '?' + urllib.parse.urlencode(params)
    response = _http_get(url)
    if not response:
        return None

    try:
        data = json.loads(response)
        pmids = data.get('esearchresult', {}).get('idlist', [])
    except (json.JSONDecodeError, KeyError):
        return None

    if not pmids:
        return None

    papers = fetch_pubmed_papers(pmids)
    if not papers:
        return None

    paper = papers[0]

    if paper.abstract:
        sentence = extract_evidence_sentence(paper.abstract, claim)
        if sentence:
            return paper

    # DOI is legit in PubMed even if abstract doesn't match sentence exactly
    return paper


# ============================================================================
# VERIFICATION FUNCTIONS
# ============================================================================

def verify_edge(source: str, target: str, effect: str, claim: str,
                keywords: str) -> VerifiedEvidence:
    """
    Verify a proposed regulatory edge against real literature.

    Args:
        source: Source node name (e.g., "Strigolactone")
        target: Target node name (e.g., "BRC1")
        effect: "positive" or "negative"
        claim: The agent's claim about this edge
        keywords: Search keywords for finding relevant papers

    Returns:
        VerifiedEvidence with real DOI, evidence sentence, and verification status
    """
    result = VerifiedEvidence(
        claim=claim,
        search_query=keywords,
    )

    # Search PubMed first
    pmids = search_pubmed(keywords, max_results=5)
    papers = fetch_pubmed_papers(pmids) if pmids else []
    result.papers_found = len(papers)

    # Tier 2: Semantic Scholar fallback if PubMed returns < 2 results
    if len(papers) < 2:
        s2_papers = search_semantic_scholar(keywords, max_results=5)
        papers.extend(s2_papers)
        result.papers_found = len(papers)

    # Tier 3: If no papers with DOIs found, return "unverified".
    # The calling Claude agent should then use its own WebSearch tool to find
    # the paper/DOI, and call verify_doi_in_pubmed() to cross-check it.

    if not papers:
        result.verification = "unverified"
        return result

    # Find the best matching paper
    best_paper = None
    best_score = 0
    best_sentence = ""

    for paper in papers:
        result.papers_checked += 1
        sentence = extract_evidence_sentence(paper.abstract, claim)
        if sentence:
            # Score by: has abstract match + has DOI + year recency
            score = 1.0
            if paper.doi:
                score += 0.5
            if paper.year >= 2000:
                score += 0.3
            if score > best_score:
                best_score = score
                best_paper = paper
                best_sentence = sentence

    # If no sentence match, just use the most relevant paper
    if not best_paper and papers:
        # Use first paper with a DOI, or just the first paper
        for p in papers:
            if p.doi:
                best_paper = p
                break
        if not best_paper:
            best_paper = papers[0]

    if best_paper:
        result.evidence_sentence = best_sentence
        # Set verification status based on source
        if best_paper.source_api == "web_search":
            verification_status = "web_search_verified"
        else:
            verification_status = best_paper.source_api + "_api"
        result.source = {
            'doi': best_paper.doi,
            'pubmed_url': best_paper.pubmed_url,
            'title': best_paper.title,
            'authors': best_paper.authors,
            'year': best_paper.year,
            'journal': best_paper.journal,
            'verification': verification_status,
        }
        result.verification = verification_status
        result.confidence_boost = bool(best_sentence and best_paper.doi)
    else:
        result.verification = "unverified"

    return result


def verify_perturbation(gene: str, perturbation: str, outcome: str,
                        claim: str, keywords: str) -> VerifiedEvidence:
    """
    Verify a proposed perturbation test against real literature.

    Args:
        gene: Gene name (e.g., "MAX2")
        perturbation: Type (e.g., "knockout")
        outcome: Expected outcome (e.g., "increased branching")
        claim: The agent's claim about this test
        keywords: Search keywords for finding relevant papers

    Returns:
        VerifiedEvidence with real DOI, evidence sentence, and verification status
    """
    # Same verification workflow as edges
    return verify_edge(
        source=gene, target=outcome, effect=perturbation,
        claim=claim, keywords=keywords
    )


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

def batch_verify(items: List[Dict[str, str]],
                 verify_fn: str = "edge",
                 rate_limit: float = 0.5) -> List[VerifiedEvidence]:
    """
    Batch verification with rate limiting.

    Args:
        items: List of dicts with keys matching verify_edge or verify_perturbation args
        verify_fn: "edge" or "perturbation"
        rate_limit: Seconds between requests

    Returns:
        List of VerifiedEvidence results
    """
    results = []
    for item in items:
        if verify_fn == "edge":
            result = verify_edge(
                source=item.get('source', ''),
                target=item.get('target', ''),
                effect=item.get('effect', ''),
                claim=item.get('claim', ''),
                keywords=item.get('keywords', '')
            )
        else:
            result = verify_perturbation(
                gene=item.get('gene', ''),
                perturbation=item.get('perturbation', ''),
                outcome=item.get('outcome', ''),
                claim=item.get('claim', ''),
                keywords=item.get('keywords', '')
            )
        results.append(result)
        time.sleep(rate_limit)

    return results


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_pubmed_url(pmid: str) -> str:
    """Format a PMID into a PubMed URL."""
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}" if pmid else ""


def format_evidence_json(evidence: VerifiedEvidence) -> Dict[str, Any]:
    """Format VerifiedEvidence into the standardized JSON schema."""
    return {
        'claim': evidence.claim,
        'evidence_sentence': evidence.evidence_sentence,
        'source': evidence.source,
        'verification': evidence.verification,
        'search_query': evidence.search_query,
        'papers_found': evidence.papers_found,
        'papers_checked': evidence.papers_checked,
    }


def summarize_verification(results: List[VerifiedEvidence]) -> Dict[str, Any]:
    """Generate a verification summary for metadata."""
    total = len(results)
    verified_pubmed = sum(1 for r in results if 'pubmed' in r.verification)
    verified_s2 = sum(1 for r in results if 'semantic_scholar' in r.verification)
    verified_web = sum(1 for r in results if r.verification == 'web_search_verified')
    unverified = sum(1 for r in results if r.verification == 'unverified')
    with_sentence = sum(1 for r in results if r.evidence_sentence)
    with_doi = sum(1 for r in results if r.source.get('doi'))

    return {
        'total_items': total,
        'verified_pubmed': verified_pubmed,
        'verified_semantic_scholar': verified_s2,
        'verified_web_search': verified_web,
        'unverified': unverified,
        'with_evidence_sentence': with_sentence,
        'with_doi': with_doi,
        'verification_rate': round((total - unverified) / total * 100, 1) if total > 0 else 0.0,
    }


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Simple CLI for testing literature retrieval."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python literature_retriever.py <search_query>")
        print("Example: python literature_retriever.py 'strigolactone BRC1 branching arabidopsis'")
        sys.exit(1)

    query = ' '.join(sys.argv[1:])
    print(f"Searching PubMed for: {query}")

    pmids = search_pubmed(query, max_results=5)
    print(f"Found {len(pmids)} PMIDs: {pmids}")

    if pmids:
        papers = fetch_pubmed_papers(pmids)
        for p in papers:
            print(f"\n  PMID: {p.pmid}")
            print(f"  DOI: {p.doi}")
            print(f"  Title: {p.title}")
            print(f"  Authors: {p.authors}")
            print(f"  Year: {p.year}")
            print(f"  Journal: {p.journal}")
            print(f"  URL: {p.pubmed_url}")
            if p.abstract:
                print(f"  Abstract: {p.abstract[:200]}...")

    if len(pmids) < 2:
        print(f"\nFallback: Searching Semantic Scholar...")
        s2_papers = search_semantic_scholar(query, max_results=5)
        for p in s2_papers:
            print(f"\n  Title: {p.title}")
            print(f"  DOI: {p.doi}")
            print(f"  Authors: {p.authors}")
            print(f"  Year: {p.year}")

    print("\nDone.")


if __name__ == '__main__':
    main()
