"""
Project-Aware Literature Review Module
======================================

This module provides:
- Project context extraction from GitHub, URLs, documents
- Introduction & Related Studies generation
- Word IEEE template integration
- Humanization for US/UK/Indian English variants
- End-to-end workflow orchestration
"""

from .project_context import ProjectContextRetriever, ProjectOverview
from .intro_generator import IntroductionGenerator, IntroductionSection
from .related_studies import RelatedStudiesGenerator, RelatedStudiesSection
from .word_template import WordTemplateHandler, TemplateInfo, DocumentSection
from .humanization import (
    HumanizationModule,
    HumanizationConfig,
    HumanizationResult,
    LanguageVariant,
    HumanizationStrength
)
from .workflow import (
    LitReviewWorkflow,
    WorkflowConfig,
    WorkflowState,
    WorkflowResult,
    WorkflowStage,
    CitationFormat
)

__all__ = [
    # Project Context
    'ProjectContextRetriever',
    'ProjectOverview',
    
    # Introduction
    'IntroductionGenerator',
    'IntroductionSection',
    
    # Related Studies
    'RelatedStudiesGenerator',
    'RelatedStudiesSection',
    
    # Word Template
    'WordTemplateHandler',
    'TemplateInfo',
    'DocumentSection',
    
    # Humanization
    'HumanizationModule',
    'HumanizationConfig',
    'HumanizationResult',
    'LanguageVariant',
    'HumanizationStrength',
    
    # Workflow
    'LitReviewWorkflow',
    'WorkflowConfig',
    'WorkflowState',
    'WorkflowResult',
    'WorkflowStage',
    'CitationFormat',
]
