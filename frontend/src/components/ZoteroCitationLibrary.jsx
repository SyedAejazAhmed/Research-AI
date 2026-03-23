import React, { useState, useEffect } from 'react';

/**
 * Zotero Citation Library Component
 * ===================================
 * Frontend interface for managing citations with Zotero-like functionality
 */

const ZoteroCitationLibrary = () => {
  const [citations, setCitations] = useState([]);
  const [collections, setCollections] = useState([]);
  const [selectedCollection, setSelectedCollection] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCitations, setSelectedCitations] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('list'); // list, grid, detail

  // Fetch citations from API
  useEffect(() => {
    fetchCitations();
    fetchCollections();
  }, []);

  const fetchCitations = async (collectionId = null) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (collectionId) params.append('collection_id', collectionId);
      if (searchQuery) params.append('q', searchQuery);

      const response = await fetch(`/api/citations?${params}`);
      const data = await response.json();
      setCitations(data.citations || []);
    } catch (error) {
      console.error('Error fetching citations:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCollections = async () => {
    try {
      const response = await fetch('/api/citations/collections');
      const data = await response.json();
      setCollections(data.collections || []);
    } catch (error) {
      console.error('Error fetching collections:', error);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchCitations(selectedCollection);
  };

  const handleCollectionSelect = (collectionId) => {
    setSelectedCollection(collectionId);
    fetchCitations(collectionId);
  };

  const handleCitationSelect = (citationId) => {
    const newSelected = new Set(selectedCitations);
    if (newSelected.has(citationId)) {
      newSelected.delete(citationId);
    } else {
      newSelected.add(citationId);
    }
    setSelectedCitations(newSelected);
  };

  const exportSelectedBibTeX = async () => {
    try {
      const citationIds = Array.from(selectedCitations);
      const response = await fetch('/api/citations/export/bibtex', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ citation_ids: citationIds })
      });
      const data = await response.json();

      // Download as file
      const blob = new Blob([data.bibtex], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'references.bib';
      a.click();
    } catch (error) {
      console.error('Export error:', error);
    }
  };

  const formatAuthors = (authors) => {
    if (!authors || authors.length === 0) return 'Unknown';
    if (authors.length === 1) return authors[0];
    if (authors.length === 2) return `${authors[0]} and ${authors[1]}`;
    return `${authors[0]} et al.`;
  };

  return (
    <div className="zotero-library-container flex h-screen bg-gray-50">
      {/* Sidebar - Collections */}
      <div className="w-64 bg-white border-r border-gray-200 overflow-y-auto">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            Citation Library
          </h2>
        </div>

        <div className="p-2">
          <button
            onClick={() => handleCollectionSelect(null)}
            className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
              selectedCollection === null
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <span className="flex items-center">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
              </svg>
              All Citations ({citations.length})
            </span>
          </button>

          <div className="mt-4">
            <h3 className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Collections
            </h3>
            {collections.map((collection) => (
              <button
                key={collection.id}
                onClick={() => handleCollectionSelect(collection.id)}
                className={`w-full text-left px-3 py-2 rounded-lg transition-colors mb-1 ${
                  selectedCollection === collection.id
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <span className="flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                  </svg>
                  <span className="truncate">{collection.name}</span>
                  <span className="ml-auto text-xs text-gray-500">
                    {collection.item_count || 0}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between mb-4">
            <form onSubmit={handleSearch} className="flex-1 max-w-2xl">
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search citations by title, author, DOI..."
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <button
                  type="submit"
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </button>
              </div>
            </form>

            <div className="flex items-center space-x-2 ml-4">
              {/* View toggle */}
              <div className="flex border border-gray-300 rounded-lg overflow-hidden">
                <button
                  onClick={() => setView('list')}
                  className={`px-3 py-2 ${view === 'list' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
                <button
                  onClick={() => setView('grid')}
                  className={`px-3 py-2 ${view === 'grid' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                  </svg>
                </button>
              </div>

              {/* Export button */}
              {selectedCitations.size > 0 && (
                <button
                  onClick={exportSelectedBibTeX}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Export BibTeX ({selectedCitations.size})
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Citations List */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : citations.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <svg className="w-16 h-16 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-lg font-medium">No citations found</p>
                <p className="text-sm mt-2">Start by adding citations to your library</p>
              </div>
            </div>
          ) : (
            <div className={view === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' : 'space-y-3'}>
              {citations.map((citation) => (
                <div
                  key={citation.id}
                  className={`bg-white rounded-lg border-2 transition-all cursor-pointer ${
                    selectedCitations.has(citation.id)
                      ? 'border-blue-500 shadow-md'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => handleCitationSelect(citation.id)}
                >
                  <div className="p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h3 className="text-base font-semibold text-gray-900 mb-1 line-clamp-2">
                          {citation.title || 'Untitled'}
                        </h3>
                        <p className="text-sm text-gray-600 mb-2">
                          {formatAuthors(JSON.parse(citation.authors || '[]'))}
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={selectedCitations.has(citation.id)}
                        onChange={() => handleCitationSelect(citation.id)}
                        className="mt-1 h-5 w-5 text-blue-600 rounded"
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>

                    <div className="flex items-center text-sm text-gray-500 space-x-4">
                      {citation.year && (
                        <span className="flex items-center">
                          <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                          </svg>
                          {citation.year}
                        </span>
                      )}
                      {citation.doi && (
                        <span className="flex items-center truncate">
                          <svg className="w-4 h-4 mr-1 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd" />
                          </svg>
                          <span className="truncate">{citation.doi}</span>
                        </span>
                      )}
                    </div>

                    {citation.abstract && (
                      <p className="mt-2 text-sm text-gray-600 line-clamp-2">
                        {citation.abstract}
                      </p>
                    )}

                    {citation.keywords && JSON.parse(citation.keywords).length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {JSON.parse(citation.keywords).slice(0, 3).map((keyword, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
                          >
                            {keyword}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ZoteroCitationLibrary;
