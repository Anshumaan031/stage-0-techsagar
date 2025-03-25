import React from 'react';
import { Search, RefreshCw, Timer, FileDown, CheckCircle, LayoutDashboard, ClipboardCheck, Globe, AlertCircle } from 'lucide-react';
import * as XLSX from 'xlsx';

interface Company {
  name: string;
  tech_area: string;
  description: string;
}

interface ValidatedCompany {
  name: string;
  is_indian: boolean;
  is_startup: boolean;
  founded_year: number;
  founders: string;
  headquarters: string;
  funding_info: string;
  validation_notes: string;
}

interface Website {
  company_name: string;
  official_website: string;
  tech_area: string;
  founded_year: number | null;
  headquarters: string | null;
  confidence_score: number;
  verification_notes: string;
}

interface CompanyWebsites {
  company_name: string;
  websites: Website[];
  summary: string;
}

interface HighConfidenceWebsite {
  name: string;
  website: string;
  tech_area: string;
  confidence: number;
}

interface WebsiteValidationResponse {
  tech_area: string;
  company_websites: CompanyWebsites[];
  count: number;
  high_confidence_websites: HighConfidenceWebsite[];
}

interface ValidationResponse {
  tech_area: string;
  validated_companies: ValidatedCompany[];
  summary: string;
  original_query: string;
}

interface ResearchData {
  tech_area: string;
  companies: Company[];
  summary: string;
  query_used: string;
}

interface ResearchParams {
  tech_area: string;
  max_results: number;
}

type Page = 'research' | 'validation' | 'websites';

function App() {
  const [currentPage, setCurrentPage] = React.useState<Page>('research');
  const [searchTerm, setSearchTerm] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);
  const [isValidating, setIsValidating] = React.useState(false);
  const [isLoadingWebsites, setIsLoadingWebsites] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [data, setData] = React.useState<ResearchData | null>(null);
  const [validationData, setValidationData] = React.useState<ValidationResponse | null>(null);
  const [websiteData, setWebsiteData] = React.useState<WebsiteValidationResponse | null>(null);
  const [techArea, setTechArea] = React.useState('Blockchain');
  const [maxResults, setMaxResults] = React.useState(20);
  const [elapsedTime, setElapsedTime] = React.useState(0);
  const timerRef = React.useRef<number>();

  React.useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const startTimer = () => {
    setElapsedTime(0);
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    timerRef.current = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);
  };

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const downloadExcel = () => {
    if (!data?.companies) return;
    
    const ws = XLSX.utils.json_to_sheet(data.companies);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Companies');
    XLSX.writeFile(wb, 'companies.xlsx');
  };

  const validateWebsites = async () => {
    if (!validationData) return;
    
    setIsLoadingWebsites(true);
    setError(null);
    setCurrentPage('websites');
    startTimer();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600000); // 10-minute timeout

    try {
      const response = await fetch('http://localhost:5000/api/websites', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Connection': 'keep-alive',
          'Keep-Alive': 'timeout=600',
        },
        body: JSON.stringify(validationData),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error('Website validation failed');
      }

      const websiteResult = await response.json();
      setWebsiteData(websiteResult);
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Request timed out after 10 minutes');
      } else {
        setError(err instanceof Error ? err.message : 'Website validation failed');
      }
    } finally {
      stopTimer();
      setIsLoadingWebsites(false);
      clearTimeout(timeoutId);
    }
  };

  const validateCompanies = async () => {
    if (!data) return;
    
    setIsValidating(true);
    setError(null);
    setCurrentPage('validation');
    startTimer();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600000); // 10-minute timeout

    try {
      const response = await fetch('http://localhost:5000/api/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Connection': 'keep-alive',
          'Keep-Alive': 'timeout=600',
        },
        body: JSON.stringify({
          companies: data.companies,
          query_used: data.query_used,
          summary: data.summary,
          tech_area: data.tech_area
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error('Validation failed');
      }

      const validationResult = await response.json();
      setValidationData(validationResult);
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Request timed out after 10 minutes');
      } else {
        setError(err instanceof Error ? err.message : 'Validation failed');
      }
    } finally {
      stopTimer();
      setIsValidating(false);
      clearTimeout(timeoutId);
    }
  };

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    startTimer();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 300000); // 5-minute timeout

    try {
      const params: ResearchParams = {
        tech_area: techArea,
        max_results: maxResults
      };
      
      const response = await fetch('http://localhost:5000/api/research', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Connection': 'keep-alive',
          'Keep-Alive': 'timeout=300',
        },
        body: JSON.stringify(params),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error('Failed to fetch data');
      }
      const jsonData = await response.json();
      setData(jsonData);
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Request timed out after 5 minutes');
      } else {
        setError(err instanceof Error ? err.message : 'An error occurred');
      }
    } finally {
      stopTimer();
      setIsLoading(false);
      clearTimeout(timeoutId);
    }
  };

  const filteredCompanies = React.useMemo(() => {
    if (!data) return [];
    return data.companies.filter(company =>
      company.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      company.description.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [data, searchTerm]);

  const renderContent = () => {
    if (currentPage === 'websites' && websiteData) {
      if (isLoadingWebsites) {
        return (
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <div className="flex items-center gap-2 text-gray-600">
              <Timer className="h-5 w-5" />
              <span>Elapsed Time: {formatTime(elapsedTime)}</span>
            </div>
            <p className="text-lg font-medium text-gray-700">Validating Websites...</p>
            <p className="text-sm text-gray-500">This may take up to 10 minutes</p>
          </div>
        );
      }

      return (
        <div className="space-y-8">
          {/* Summary Information Table */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Summary Information</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tech Area</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total Companies</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-900">{websiteData.tech_area}</td>
                    <td className="px-6 py-4 text-sm text-gray-900">{websiteData.count}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* High Confidence Websites Table */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">High Confidence Websites</h2>
            {websiteData.high_confidence_websites && websiteData.high_confidence_websites.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Company Name</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Website</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tech Area</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {websiteData.high_confidence_websites.map((website, index) => (
                      <tr key={website.website} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-6 py-4 text-sm text-gray-900">{website.name}</td>
                        <td className="px-6 py-4">
                          <a 
                            href={website.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 flex items-center gap-2"
                          >
                            <Globe className="h-4 w-4" />
                            {website.website}
                          </a>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500">{website.tech_area}</td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            website.confidence >= 8 
                              ? 'bg-green-100 text-green-800'
                              : website.confidence >= 5
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {website.confidence}/10
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 bg-gray-50 rounded-lg">
                <AlertCircle className="h-8 w-8 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600">No high confidence websites found</p>
              </div>
            )}
          </div>

          {/* Detailed Company Websites */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Detailed Company Websites</h2>
            {websiteData.company_websites && websiteData.company_websites.length > 0 ? (
              websiteData.company_websites.map((companyData) => (
                <div key={companyData.company_name} className="mb-8 border-b pb-6 last:border-b-0">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4">{companyData.company_name}</h3>
                  <p className="text-gray-600 mb-4">{companyData.summary}</p>
                  
                  {companyData.websites && companyData.websites.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Website</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tech Area</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Founded</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">HQ</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {companyData.websites.map((website, index) => (
                            <tr key={website.official_website} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                              <td className="px-6 py-4">
                                <a 
                                  href={website.official_website}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:text-blue-800 flex items-center gap-2"
                                >
                                  <Globe className="h-4 w-4" />
                                  {website.official_website}
                                </a>
                                <div className="text-xs text-gray-500 mt-1">{website.verification_notes}</div>
                              </td>
                              <td className="px-6 py-4 text-sm text-gray-500">{website.tech_area || 'N/A'}</td>
                              <td className="px-6 py-4 text-sm text-gray-500">{website.founded_year || 'N/A'}</td>
                              <td className="px-6 py-4 text-sm text-gray-500">{website.headquarters || 'N/A'}</td>
                              <td className="px-6 py-4">
                                <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                  website.confidence_score >= 8 
                                    ? 'bg-green-100 text-green-800'
                                    : website.confidence_score >= 5
                                    ? 'bg-yellow-100 text-yellow-800'
                                    : 'bg-red-100 text-red-800'
                                }`}>
                                  {website.confidence_score}/10
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="bg-gray-50 rounded-lg p-4 flex items-center gap-3">
                      <AlertCircle className="h-5 w-5 text-gray-400" />
                      <p className="text-gray-600">No website information available</p>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-8 bg-gray-50 rounded-lg">
                <AlertCircle className="h-8 w-8 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600">No company website data available</p>
              </div>
            )}
          </div>
        </div>
      );
    }

    if (currentPage === 'validation') {
      if (isValidating) {
        return (
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <div className="flex items-center gap-2 text-gray-600">
              <Timer className="h-5 w-5" />
              <span>Elapsed Time: {formatTime(elapsedTime)}</span>
            </div>
            <p className="text-lg font-medium text-gray-700">Validating Companies...</p>
            <p className="text-sm text-gray-500">This may take up to 10 minutes</p>
          </div>
        );
      }

      if (!validationData) {
        return (
          <div className="text-center py-12">
            <p className="text-gray-600">No validation data available. Please validate companies first.</p>
          </div>
        );
      }

      return (
        <div className="space-y-8">
          {/* Validation Summary */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Validation Summary</h2>
            <p className="text-gray-600 mb-6">{validationData.summary}</p>
            <p className="text-sm text-gray-500">Original Query: {validationData.original_query}</p>
          </div>

          {/* Validation Results Table */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-800">Validation Results</h2>
              <button
                onClick={validateWebsites}
                disabled={isLoadingWebsites}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-blue-400"
              >
                <Globe className="h-4 w-4" />
                {isLoadingWebsites ? 'Validating Websites...' : 'Validate Websites'}
              </button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Company</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Founded</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Founders</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Funding</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {validationData.validated_companies.map((company, index) => (
                    <tr key={company.name} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900">{company.name}</div>
                        <div className="text-xs text-gray-500 mt-1">{company.validation_notes}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">{company.founded_year}</td>
                      <td className="px-6 py-4 text-sm text-gray-500">{company.founders}</td>
                      <td className="px-6 py-4 text-sm text-gray-500">{company.headquarters}</td>
                      <td className="px-6 py-4 text-sm text-gray-500">{company.funding_info}</td>
                      <td className="px-6 py-4">
                        <div className="space-y-1">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            company.is_indian
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {company.is_indian ? 'Indian' : 'Non-Indian'}
                          </span>
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            company.is_startup
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {company.is_startup ? 'Startup' : 'Established'}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="mb-8 space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Tech Area</label>
              <input
                type="text"
                value={techArea}
                onChange={(e) => setTechArea(e.target.value)}
                placeholder="Enter tech area..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Maximum Results
              </label>
              <input
                type="number"
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
                min="1"
                max="100"
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <button
              onClick={fetchData}
              disabled={isLoading || !techArea.trim()}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-blue-400"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              {isLoading ? 'Searching...' : 'Search Companies'}
            </button>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          {data && <p className="text-gray-600 mb-6">{data.summary}</p>}
          
          <div className="relative mb-6">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search companies..."
              className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <div className="flex items-center gap-2 text-gray-600">
                <Timer className="h-5 w-5" />
                <span>Elapsed Time: {formatTime(elapsedTime)}</span>
              </div>
              <p className="text-sm text-gray-500">This may take a few minutes...</p>
            </div>
          ) : (
            <>
              {data && data.companies.length > 0 && (
                <div className="flex justify-end gap-4 mb-4">
                  <button
                    onClick={downloadExcel}
                    className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:text-blue-800"
                  >
                    <FileDown className="h-4 w-4" />
                    Download Excel
                  </button>
                  <button
                    onClick={validateCompanies}
                    disabled={isValidating}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:bg-green-400"
                  >
                    <CheckCircle className="h-4 w-4" />
                    {isValidating ? 'Validating...' : 'Validate Companies'}
                  </button>
                </div>
              )}
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Company Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Description
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredCompanies.map((company, index) => (
                      <tr key={company.name} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{company.name}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm text-gray-500">{company.description}</div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filteredCompanies.length === 0 && !isLoading && (
                  <div className="text-center py-12 text-gray-500">
                    {data ? 'No companies found matching your search.' : 'Configure your search parameters and click "Search Companies" to begin.'}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      <div className="flex h-screen">
        {/* Sidebar */}
        <div className="w-64 bg-white shadow-lg">
          <div className="p-6">
            <h1 className="text-xl font-bold text-gray-800 mb-8">Startup Research</h1>
            <nav className="space-y-2">
              <button
                onClick={() => setCurrentPage('research')}
                className={`w-full flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  currentPage === 'research'
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <LayoutDashboard className="h-5 w-5" />
                Research
              </button>
              <button
                onClick={() => setCurrentPage('validation')}
                className={`w-full flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  currentPage === 'validation'
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <ClipboardCheck className="h-5 w-5" />
                Validation
              </button>
              <button
                onClick={() => setCurrentPage('websites')}
                className={`w-full flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  currentPage === 'websites'
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Globe className="h-5 w-5" />
                Websites
              </button>
            </nav>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-auto p-6">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}

export default App;