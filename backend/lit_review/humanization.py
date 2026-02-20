"""
Humanization Module
===================

Applies humanization transformations to academic text:
- Regional English variants (US, UK, Indian)
- AI pattern diversification
- Natural writing style injection
- Sentence structure variation
"""

import re
import random
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LanguageVariant(Enum):
    """Supported language variants."""
    US_ENGLISH = "us"
    UK_ENGLISH = "uk"
    INDIAN_ENGLISH = "indian"


class HumanizationStrength(Enum):
    """Humanization strength levels."""
    LIGHT = "light"       # Minimal changes
    MODERATE = "moderate"  # Balanced changes
    STRONG = "strong"      # Significant changes


@dataclass
class HumanizationConfig:
    """Configuration for humanization."""
    variant: LanguageVariant = LanguageVariant.US_ENGLISH
    strength: HumanizationStrength = HumanizationStrength.MODERATE
    preserve_technical: bool = True
    preserve_citations: bool = True
    vary_sentence_length: bool = True
    add_transitions: bool = True
    diversify_vocabulary: bool = True


@dataclass
class HumanizationResult:
    """Result of humanization."""
    original: str
    humanized: str
    changes_made: int
    variant_applied: str
    confidence: float


# Spelling differences: US -> UK
US_TO_UK_SPELLINGS = {
    'behavior': 'behaviour',
    'color': 'colour',
    'favor': 'favour',
    'honor': 'honour',
    'labor': 'labour',
    'neighbor': 'neighbour',
    'analyze': 'analyse',
    'optimize': 'optimise',
    'recognize': 'recognise',
    'organize': 'organise',
    'realize': 'realise',
    'utilize': 'utilise',
    'center': 'centre',
    'theater': 'theatre',
    'meter': 'metre',
    'fiber': 'fibre',
    'program': 'programme',
    'defense': 'defence',
    'offense': 'offence',
    'license': 'licence',
    'practice': 'practise',
    'catalog': 'catalogue',
    'dialog': 'dialogue',
    'modeling': 'modelling',
    'traveling': 'travelling',
    'labeled': 'labelled',
    'signaling': 'signalling',
}

# UK -> US (reverse)
UK_TO_US_SPELLINGS = {v: k for k, v in US_TO_UK_SPELLINGS.items()}

# Indian English specific patterns
INDIAN_ENGLISH_PATTERNS = {
    # Idioms and phrases
    'as such': 'therefore',
    'do the needful': 'take necessary action',
    'kindly': 'please',
    'prepone': 'move forward',
    'revert back': 'respond',
}

# Common academic transitions
ACADEMIC_TRANSITIONS = {
    'start': [
        'To begin with,',
        'First and foremost,',
        'Initially,',
        'At the outset,',
    ],
    'addition': [
        'Furthermore,',
        'Moreover,',
        'Additionally,',
        'In addition,',
        'Besides,',
        'What is more,',
    ],
    'contrast': [
        'However,',
        'Nevertheless,',
        'On the other hand,',
        'In contrast,',
        'Conversely,',
        'Yet,',
    ],
    'result': [
        'Therefore,',
        'Consequently,',
        'As a result,',
        'Thus,',
        'Hence,',
        'Accordingly,',
    ],
    'example': [
        'For instance,',
        'For example,',
        'To illustrate,',
        'As an illustration,',
        'Specifically,',
    ],
    'emphasis': [
        'Indeed,',
        'In fact,',
        'Notably,',
        'Significantly,',
        'Importantly,',
    ],
    'conclusion': [
        'In conclusion,',
        'To summarize,',
        'In summary,',
        'Overall,',
        'In essence,',
    ],
}

# Vocabulary diversification - synonyms for common academic words
VOCABULARY_ALTERNATIVES = {
    'significant': ['notable', 'substantial', 'considerable', 'marked', 'meaningful'],
    'important': ['crucial', 'vital', 'essential', 'key', 'critical'],
    'show': ['demonstrate', 'reveal', 'indicate', 'illustrate', 'exhibit'],
    'use': ['employ', 'utilize', 'apply', 'leverage', 'adopt'],
    'study': ['investigation', 'research', 'analysis', 'examination', 'inquiry'],
    'method': ['approach', 'technique', 'methodology', 'procedure', 'strategy'],
    'result': ['outcome', 'finding', 'consequence', 'effect', 'conclusion'],
    'increase': ['enhance', 'improve', 'boost', 'elevate', 'amplify'],
    'decrease': ['reduce', 'diminish', 'lower', 'decline', 'minimize'],
    'develop': ['create', 'design', 'establish', 'formulate', 'construct'],
    'propose': ['suggest', 'present', 'introduce', 'put forward', 'advance'],
    'achieve': ['accomplish', 'attain', 'realize', 'reach', 'obtain'],
    'large': ['substantial', 'extensive', 'considerable', 'sizable', 'major'],
    'small': ['minor', 'limited', 'modest', 'slight', 'minimal'],
    'good': ['effective', 'favorable', 'positive', 'beneficial', 'advantageous'],
    'bad': ['negative', 'unfavorable', 'adverse', 'detrimental', 'problematic'],
    'new': ['novel', 'innovative', 'emerging', 'recent', 'modern'],
    'old': ['traditional', 'conventional', 'established', 'classical', 'existing'],
}

# AI-generated text patterns to diversify
AI_PATTERNS_TO_VARY = [
    # Repetitive sentence starters
    (r'^(This|It|The|We|They)\s', [
        'Notably, this ',
        'In particular, it ',
        'Interestingly, the ',
        'Our analysis shows that we ',
        'The evidence suggests they ',
    ]),
    # Generic phrases
    (r'it is important to note that', [
        'notably',
        'significantly',
        'it bears mentioning that',
        'worth noting is that',
    ]),
    (r'in order to', ['to', 'so as to', 'with the aim of', 'for the purpose of']),
    (r'a lot of', ['numerous', 'many', 'substantial', 'considerable']),
    (r'due to the fact that', ['because', 'since', 'as', 'given that']),
    (r'in spite of the fact that', ['although', 'despite', 'even though']),
    (r'at the present time', ['currently', 'now', 'presently', 'at present']),
    (r'in the event that', ['if', 'should', 'in case']),
]


class HumanizationModule:
    """
    Applies humanization transformations to academic text.
    
    Features:
    - Regional English variant conversion (US/UK/Indian)
    - AI pattern diversification
    - Natural writing style injection
    - Sentence structure variation
    - Vocabulary diversification
    - Technical term preservation
    """
    
    def __init__(self, config: HumanizationConfig = None):
        """
        Initialize the module.
        
        Args:
            config: Humanization configuration
        """
        self.config = config or HumanizationConfig()
        self._rng = random.Random()
    
    def set_seed(self, seed: int):
        """Set random seed for reproducibility."""
        self._rng.seed(seed)
    
    def humanize(
        self,
        text: str,
        config: HumanizationConfig = None
    ) -> HumanizationResult:
        """
        Apply humanization to text.
        
        Args:
            text: Text to humanize
            config: Optional config override
            
        Returns:
            HumanizationResult with original and humanized text
        """
        cfg = config or self.config
        result = text
        changes = 0
        
        # Extract and preserve citations
        citations = []
        if cfg.preserve_citations:
            result, citations = self._extract_citations(result)
        
        # Extract and preserve technical terms
        technical_terms = []
        if cfg.preserve_technical:
            result, technical_terms = self._extract_technical_terms(result)
        
        # Apply language variant
        result, variant_changes = self._apply_variant(result, cfg.variant)
        changes += variant_changes
        
        # Diversify vocabulary
        if cfg.diversify_vocabulary:
            result, vocab_changes = self._diversify_vocabulary(result, cfg.strength)
            changes += vocab_changes
        
        # Vary sentence structure
        if cfg.vary_sentence_length:
            result, struct_changes = self._vary_sentence_structure(result, cfg.strength)
            changes += struct_changes
        
        # Diversify AI patterns
        result, ai_changes = self._diversify_ai_patterns(result, cfg.strength)
        changes += ai_changes
        
        # Add transitions
        if cfg.add_transitions:
            result, trans_changes = self._add_transitions(result, cfg.strength)
            changes += trans_changes
        
        # Restore technical terms
        if cfg.preserve_technical:
            result = self._restore_technical_terms(result, technical_terms)
        
        # Restore citations
        if cfg.preserve_citations:
            result = self._restore_citations(result, citations)
        
        # Calculate confidence based on changes
        confidence = min(1.0, changes / max(len(text.split()), 1) * 10)
        
        return HumanizationResult(
            original=text,
            humanized=result,
            changes_made=changes,
            variant_applied=cfg.variant.value,
            confidence=confidence
        )
    
    def _extract_citations(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """Extract citations for preservation."""
        citations = []
        counter = [0]
        
        def replace_citation(match):
            placeholder = f"__CITATION_{counter[0]}__"
            citations.append((placeholder, match.group(0)))
            counter[0] += 1
            return placeholder
        
        # Match various citation formats
        patterns = [
            r'\[[0-9,\s-]+\]',  # [1], [1,2], [1-5]
            r'\([A-Za-z]+\s*et\s*al\.?,?\s*\d{4}\)',  # (Author et al., 2023)
            r'\([A-Za-z]+,?\s*\d{4}\)',  # (Author, 2023)
            r'\([A-Za-z]+\s*&\s*[A-Za-z]+,?\s*\d{4}\)',  # (Author & Author, 2023)
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, replace_citation, text)
        
        return text, citations
    
    def _restore_citations(self, text: str, citations: List[Tuple[str, str]]) -> str:
        """Restore citations after processing."""
        for placeholder, original in citations:
            text = text.replace(placeholder, original)
        return text
    
    def _extract_technical_terms(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """Extract technical terms for preservation."""
        technical_terms = []
        counter = [0]
        
        def replace_term(match):
            placeholder = f"__TECH_{counter[0]}__"
            technical_terms.append((placeholder, match.group(0)))
            counter[0] += 1
            return placeholder
        
        # Match technical patterns
        patterns = [
            r'\b[A-Z]{2,}[a-z]*\b',  # Acronyms like CNN, LSTM
            r'\b[a-z]+[A-Z][a-zA-Z]*\b',  # camelCase
            r'\b\d+[a-zA-Z]+\b',  # Numbers with units like 100ms
            r'`[^`]+`',  # Code in backticks
            r'\$[^$]+\$',  # Math expressions
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, replace_term, text)
        
        return text, technical_terms
    
    def _restore_technical_terms(self, text: str, terms: List[Tuple[str, str]]) -> str:
        """Restore technical terms after processing."""
        for placeholder, original in terms:
            text = text.replace(placeholder, original)
        return text
    
    def _apply_variant(
        self,
        text: str,
        variant: LanguageVariant
    ) -> Tuple[str, int]:
        """Apply regional language variant."""
        changes = 0
        
        if variant == LanguageVariant.UK_ENGLISH:
            for us, uk in US_TO_UK_SPELLINGS.items():
                pattern = re.compile(re.escape(us), re.IGNORECASE)
                matches = pattern.findall(text)
                if matches:
                    changes += len(matches)
                    text = pattern.sub(
                        lambda m: uk if m.group().islower() else uk.capitalize(),
                        text
                    )
        
        elif variant == LanguageVariant.US_ENGLISH:
            for uk, us in UK_TO_US_SPELLINGS.items():
                pattern = re.compile(re.escape(uk), re.IGNORECASE)
                matches = pattern.findall(text)
                if matches:
                    changes += len(matches)
                    text = pattern.sub(
                        lambda m: us if m.group().islower() else us.capitalize(),
                        text
                    )
        
        elif variant == LanguageVariant.INDIAN_ENGLISH:
            # Apply UK spellings first (Indian English uses UK spellings)
            for us, uk in US_TO_UK_SPELLINGS.items():
                pattern = re.compile(re.escape(us), re.IGNORECASE)
                matches = pattern.findall(text)
                if matches:
                    changes += len(matches)
                    text = pattern.sub(
                        lambda m: uk if m.group().islower() else uk.capitalize(),
                        text
                    )
            
            # Apply Indian English specific patterns
            for pattern, replacement in INDIAN_ENGLISH_PATTERNS.items():
                if pattern in text.lower():
                    text = re.sub(
                        re.escape(pattern),
                        replacement,
                        text,
                        flags=re.IGNORECASE
                    )
                    changes += 1
        
        return text, changes
    
    def _diversify_vocabulary(
        self,
        text: str,
        strength: HumanizationStrength
    ) -> Tuple[str, int]:
        """Diversify vocabulary using synonyms."""
        changes = 0
        
        # Determine replacement probability based on strength
        prob = {
            HumanizationStrength.LIGHT: 0.1,
            HumanizationStrength.MODERATE: 0.3,
            HumanizationStrength.STRONG: 0.5,
        }[strength]
        
        words = text.split()
        new_words = []
        
        for word in words:
            lower_word = word.lower().strip('.,!?;:')
            
            if lower_word in VOCABULARY_ALTERNATIVES and self._rng.random() < prob:
                alternatives = VOCABULARY_ALTERNATIVES[lower_word]
                replacement = self._rng.choice(alternatives)
                
                # Preserve case
                if word[0].isupper():
                    replacement = replacement.capitalize()
                
                # Preserve punctuation
                if word[-1] in '.,!?;:':
                    replacement += word[-1]
                
                new_words.append(replacement)
                changes += 1
            else:
                new_words.append(word)
        
        return ' '.join(new_words), changes
    
    def _vary_sentence_structure(
        self,
        text: str,
        strength: HumanizationStrength
    ) -> Tuple[str, int]:
        """Vary sentence structure for more natural flow."""
        changes = 0
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Determine variation probability
        prob = {
            HumanizationStrength.LIGHT: 0.1,
            HumanizationStrength.MODERATE: 0.2,
            HumanizationStrength.STRONG: 0.35,
        }[strength]
        
        new_sentences = []
        prev_len = 0
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            words = sentence.split()
            curr_len = len(words)
            
            # Split long sentences occasionally
            if curr_len > 30 and self._rng.random() < prob:
                # Find a good split point (after conjunctions)
                split_words = ['and', 'but', 'however', 'therefore', 'thus']
                mid = len(words) // 2
                
                for j in range(mid - 5, mid + 5):
                    if 0 < j < len(words) and words[j].lower() in split_words:
                        # Split at this point
                        first_half = ' '.join(words[:j])
                        second_half = ' '.join(words[j:])
                        
                        if not first_half.endswith('.'):
                            first_half += '.'
                        second_half = second_half.capitalize()
                        
                        new_sentences.append(first_half)
                        new_sentences.append(second_half)
                        changes += 1
                        break
                else:
                    new_sentences.append(sentence)
            
            # Combine short sentences occasionally
            elif curr_len < 8 and prev_len < 8 and i > 0 and self._rng.random() < prob:
                if new_sentences:
                    prev = new_sentences.pop()
                    if prev.endswith('.'):
                        prev = prev[:-1]
                    combined = f"{prev}, and {sentence.lower()}"
                    new_sentences.append(combined)
                    changes += 1
                else:
                    new_sentences.append(sentence)
            else:
                new_sentences.append(sentence)
            
            prev_len = curr_len
        
        return ' '.join(new_sentences), changes
    
    def _diversify_ai_patterns(
        self,
        text: str,
        strength: HumanizationStrength
    ) -> Tuple[str, int]:
        """Diversify patterns common in AI-generated text."""
        changes = 0
        
        prob = {
            HumanizationStrength.LIGHT: 0.2,
            HumanizationStrength.MODERATE: 0.4,
            HumanizationStrength.STRONG: 0.6,
        }[strength]
        
        for pattern, alternatives in AI_PATTERNS_TO_VARY:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                if self._rng.random() < prob:
                    replacement = self._rng.choice(alternatives)
                    text = re.sub(
                        re.escape(match),
                        replacement,
                        text,
                        count=1,
                        flags=re.IGNORECASE
                    )
                    changes += 1
        
        return text, changes
    
    def _add_transitions(
        self,
        text: str,
        strength: HumanizationStrength
    ) -> Tuple[str, int]:
        """Add transitional phrases for better flow."""
        changes = 0
        
        prob = {
            HumanizationStrength.LIGHT: 0.05,
            HumanizationStrength.MODERATE: 0.1,
            HumanizationStrength.STRONG: 0.15,
        }[strength]
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        new_sentences = []
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Don't add transition if sentence already has one
            has_transition = any(
                sentence.lower().startswith(t.lower().strip(','))
                for transitions in ACADEMIC_TRANSITIONS.values()
                for t in transitions
            )
            
            if i > 0 and not has_transition and self._rng.random() < prob:
                # Determine appropriate transition type
                prev = new_sentences[-1] if new_sentences else ""
                
                if 'however' in prev.lower() or 'but' in prev.lower():
                    category = 'result'
                elif 'example' in prev.lower() or 'instance' in prev.lower():
                    category = 'addition'
                elif i == len(sentences) - 1:
                    category = 'conclusion'
                else:
                    category = self._rng.choice(['addition', 'emphasis'])
                
                transition = self._rng.choice(ACADEMIC_TRANSITIONS[category])
                sentence = f"{transition} {sentence[0].lower()}{sentence[1:]}"
                changes += 1
            
            new_sentences.append(sentence)
        
        return ' '.join(new_sentences), changes
    
    def convert_to_variant(
        self,
        text: str,
        variant: LanguageVariant
    ) -> HumanizationResult:
        """
        Convert text to a specific language variant.
        
        Args:
            text: Text to convert
            variant: Target language variant
            
        Returns:
            HumanizationResult
        """
        config = HumanizationConfig(
            variant=variant,
            strength=HumanizationStrength.MODERATE,
            preserve_technical=True,
            preserve_citations=True,
            vary_sentence_length=False,
            add_transitions=False,
            diversify_vocabulary=False,
        )
        return self.humanize(text, config)
    
    def detect_variant(self, text: str) -> LanguageVariant:
        """
        Detect the language variant of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected LanguageVariant
        """
        us_count = 0
        uk_count = 0
        
        text_lower = text.lower()
        
        for us_word in US_TO_UK_SPELLINGS.keys():
            if us_word in text_lower:
                us_count += text_lower.count(us_word)
        
        for uk_word in UK_TO_US_SPELLINGS.keys():
            if uk_word in text_lower:
                uk_count += text_lower.count(uk_word)
        
        # Check for Indian English patterns
        indian_count = sum(
            1 for pattern in INDIAN_ENGLISH_PATTERNS.keys()
            if pattern in text_lower
        )
        
        if indian_count > 0:
            return LanguageVariant.INDIAN_ENGLISH
        elif uk_count > us_count:
            return LanguageVariant.UK_ENGLISH
        else:
            return LanguageVariant.US_ENGLISH
    
    def get_statistics(self, text: str) -> Dict[str, Any]:
        """
        Get statistics about text that may indicate AI generation.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of statistics
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        words = text.split()
        
        # Sentence length statistics
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        avg_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
        
        # Vocabulary diversity (unique words / total words)
        unique_words = set(word.lower().strip('.,!?;:') for word in words)
        diversity = len(unique_words) / len(words) if words else 0
        
        # Count common AI patterns
        ai_pattern_count = 0
        for pattern, _ in AI_PATTERNS_TO_VARY:
            ai_pattern_count += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Transition word count
        transition_count = 0
        for transitions in ACADEMIC_TRANSITIONS.values():
            for t in transitions:
                transition_count += text.lower().count(t.lower().strip(','))
        
        return {
            'sentence_count': len(sentence_lengths),
            'word_count': len(words),
            'avg_sentence_length': round(avg_length, 2),
            'vocabulary_diversity': round(diversity, 3),
            'ai_pattern_count': ai_pattern_count,
            'transition_count': transition_count,
            'detected_variant': self.detect_variant(text).value,
        }
