'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { chatApi, pdfApi, PDFSessionInfo } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  BookOpen,
  LogOut,
  FileText,
  User,
  Hash,
  Upload as UploadIcon,
  HelpCircle,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Brain,
  MessageSquare,
  StickyNote,
  Menu,
  Settings,
  Target,
  CheckCircle2,
  Zap,
  Copy
} from 'lucide-react';

interface Question {
  id: string;
  question: string;
  answer?: string;
  loading?: boolean;
}

interface Chapter {
  id: string;
  title: string;
  questions: Question[];
  expanded: boolean;
  loading: boolean;
}

export default function QAPage() {
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [pdfInfo, setPdfInfo] = useState<PDFSessionInfo | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [generatingQuestions, setGeneratingQuestions] = useState(false);
  const [testingAI, setTestingAI] = useState(false);
  const [questionTopic, setQuestionTopic] = useState('');
  const [questionCount, setQuestionCount] = useState(25);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const { logout, user } = useAuth();
  const router = useRouter();

  // Load PDF info on mount
  React.useEffect(() => {
    const loadPDFInfo = async () => {
      console.log('[QA Page] Loading PDF info...');
      try {
        const info = await pdfApi.getPDFInfo();
        console.log('[QA Page] PDF info loaded successfully:', info);
        setPdfInfo(info);
        setInitialLoading(false);
      } catch (error: any) {
        console.error('[QA Page] Failed to load PDF info:', error);
        console.error('[QA Page] Error details:', error.response?.data || error.message);
        setInitialLoading(false);
        
        // Show error and redirect after a brief delay
        console.log('[QA Page] No PDF selected, redirecting in 2 seconds...');
        setTimeout(() => {
          router.push('/upload');
        }, 2000);
      }
    };

    loadPDFInfo();
  }, [router]);


  const generateChapterQuestions = async (topic?: string) => {
    if (!pdfInfo) return;

    setGeneratingQuestions(true);
    try {
      const topicToUse = topic || questionTopic.trim();
      console.log('Starting question generation for:', pdfInfo.filename, 'Topic:', topicToUse);

      // Use the dedicated question generation endpoint that includes full PDF content
      const response = await chatApi.generateQuestions(topicToUse, questionCount);

      console.log('AI Response received:', response.response.substring(0, 200) + '...');

      // Parse the AI response to extract chapters and questions
      const aiResponse = response.response;

      // Try to extract JSON from the response
      let jsonMatch = aiResponse.match(/\{[\s\S]*\}/);

      if (!jsonMatch) {
        // Try to find JSON between code blocks
        const codeBlockMatch = aiResponse.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
        if (codeBlockMatch) {
          jsonMatch = [codeBlockMatch[1]];
        }
      }

      if (jsonMatch) {
        try {
          const parsedData = JSON.parse(jsonMatch[0]);
          console.log('Parsed data:', parsedData);

          if (parsedData.questions && Array.isArray(parsedData.questions)) {
            // Create a single chapter with all questions
            const generatedChapters: Chapter[] = [{
              id: 'main-questions',
              title: `Questions for: ${pdfInfo?.filename}${topicToUse ? ` - Topic: ${topicToUse}` : ''}`,
              questions: parsedData.questions.map((q: string, qIndex: number) => ({
                id: `q-${qIndex}`,
                question: q,
                answer: undefined,
                loading: false
              })),
              expanded: true, // Always expanded since there's only one section
              loading: false
            }];

            console.log('Generated questions:', parsedData.questions.length);
            setChapters(generatedChapters);
          } else {
            throw new Error('Invalid questions structure - expected questions array');
          }
        } catch (parseError) {
          console.error('JSON parsing error:', parseError);
          console.log('Raw response:', aiResponse);
          createDefaultChapters();
        }
      } else {
        console.log('No JSON found in response:', aiResponse);
        createDefaultChapters();
      }
    } catch (error) {
      console.error('Error generating questions:', error);
      createDefaultChapters();
    } finally {
      setGeneratingQuestions(false);
    }
  };

  const createDefaultChapters = async () => {
    console.log('Creating default chapters...');

    // Try a simpler approach for question generation using the dedicated endpoint
    try {
      const response = await chatApi.generateQuestions();

      // Try to parse the JSON response from the dedicated endpoint
      const aiResponse = response.response;
      let jsonMatch = aiResponse.match(/\{[\s\S]*\}/);

      if (!jsonMatch) {
        const codeBlockMatch = aiResponse.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
        if (codeBlockMatch) {
          jsonMatch = [codeBlockMatch[1]];
        }
      }

      if (jsonMatch) {
        try {
          const parsedData = JSON.parse(jsonMatch[0]);
          console.log('Parsed data from default chapters:', parsedData);

          if (parsedData.questions && Array.isArray(parsedData.questions)) {
            // Create a single chapter with all questions
            const generatedChapters: Chapter[] = [{
              id: 'main-questions',
              title: `Questions for: ${pdfInfo?.filename}${questionTopic.trim() ? ` - Topic: ${questionTopic.trim()}` : ''}`,
              questions: parsedData.questions.map((q: string, qIndex: number) => ({
                id: `q-${qIndex}`,
                question: q,
                answer: undefined,
                loading: false
              })),
              expanded: true,
              loading: false
            }];

            if (generatedChapters[0].questions.length > 0) {
              setChapters(generatedChapters);
              return;
            }
          }
        } catch (parseError) {
          console.error('JSON parsing error in default chapters:', parseError);
        }
      }

      // Final fallback
      setChapters([{
        id: 'chapter-1',
        title: 'Document Analysis',
        questions: Array.from({ length: 10 }, (_, i) => ({
          id: `q-1-${i}`,
          question: `What are the key points discussed in this document?`,
          answer: undefined,
          loading: false
        })),
        expanded: false,
        loading: false
      }]);
    } catch (error) {
      console.error('Error in default chapters:', error);
      // Final fallback
      setChapters([{
        id: 'chapter-1',
        title: 'Document Analysis',
        questions: Array.from({ length: 10 }, (_, i) => ({
          id: `q-1-${i}`,
          question: `What are the key points discussed in this document?`,
          answer: undefined,
          loading: false
        })),
        expanded: false,
        loading: false
      }]);
    }
  };

  const toggleChapter = (chapterId: string) => {
    setChapters(prev => prev.map(chapter =>
      chapter.id === chapterId
        ? { ...chapter, expanded: !chapter.expanded }
        : chapter
    ));
  };

  const handleQuestionClick = async (chapterId: string, questionId: string) => {
    const chapter = chapters.find(c => c.id === chapterId);
    const question = chapter?.questions.find(q => q.id === questionId);

    if (!question || question.answer) return;

    console.log('Answering question:', question.question);

    // Set loading state for this question
    setChapters(prev => prev.map(chapter =>
      chapter.id === chapterId
        ? {
          ...chapter,
          questions: chapter.questions.map(q =>
            q.id === questionId ? { ...q, loading: true } : q
          )
        }
        : chapter
    ));

    try {
      const response = await chatApi.sendMessage(`You are an educational AI assistant. Based on the FULL content of the document "${pdfInfo?.filename}", please provide a comprehensive and detailed answer to this question:

QUESTION: "${question.question}"

REQUIREMENTS:
1. Use ONLY information from the document content
2. Provide specific details, examples, and explanations from the text
3. Make the answer educational and easy to understand
4. Include relevant quotes or references from the document when applicable
5. Structure the answer clearly with proper formatting
6. If the question asks for examples, provide the actual examples from the document
7. If the question asks for definitions, use the exact definitions from the text

Please provide a thorough, well-structured answer that helps the user learn from the document content.`);

      console.log('Answer received for question:', question.question);

      // Update the question with the answer
      setChapters(prev => prev.map(chapter =>
        chapter.id === chapterId
          ? {
            ...chapter,
            questions: chapter.questions.map(q =>
              q.id === questionId
                ? { ...q, answer: response.response, loading: false }
                : q
            )
          }
          : chapter
      ));
    } catch (error) {
      console.error('Error getting answer:', error);
      setChapters(prev => prev.map(chapter =>
        chapter.id === chapterId
          ? {
            ...chapter,
            questions: chapter.questions.map(q =>
              q.id === questionId
                ? { ...q, loading: false }
                : q
            )
          }
          : chapter
      ));
    }
  };

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    if (dateString === 'Unknown') return 'Unknown';
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return 'Unknown';
    }
  };

  const testAIConnection = async () => {
    setTestingAI(true);
    try {
      const response = await chatApi.sendMessage("Please respond with 'AI connection working' to test the connection.");
      alert(`AI Response: ${response.response}`);
    } catch (error) {
      alert(`AI Connection Error: ${error}`);
    } finally {
      setTestingAI(false);
    }
  };

  if (initialLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#FFE8D6' }}>
        <div className="text-center">
          <div className="p-4 rounded-2xl w-16 h-16 mx-auto mb-4 flex items-center justify-center shadow-lg animate-pulse"
            style={{ backgroundColor: '#CB997E' }}>
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h3 className="text-xl font-bold mb-2" style={{ color: '#6B705C' }}>Loading Q&A Session</h3>
          <p style={{ color: '#A5A58D' }}>Preparing your learning environment...</p>
        </div>
      </div>
    );
  }

  // Show message if no PDF is selected
  if (!pdfInfo) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#FFE8D6' }}>
        <div className="text-center max-w-md mx-auto p-8">
          <div className="p-4 rounded-2xl w-16 h-16 mx-auto mb-4 flex items-center justify-center shadow-lg"
            style={{ backgroundColor: '#CB997E' }}>
            <UploadIcon className="h-8 w-8 text-white" />
          </div>
          <h3 className="text-xl font-bold mb-2" style={{ color: '#6B705C' }}>No PDF Selected</h3>
          <p className="mb-6" style={{ color: '#A5A58D' }}>
            Please upload or select a PDF document to start generating questions.
          </p>
          <p className="text-sm mb-6" style={{ color: '#A5A58D' }}>
            Redirecting to upload page...
          </p>
        </div>
      </div>
    );
  }

  const navigationItems = [
    { icon: MessageSquare, label: 'Chat', path: '/chat' },
    { icon: HelpCircle, label: 'Q&A Genration', path: '/qa', active: true },
    { icon: Brain, label: 'Answer Quiz', path: '/answer-questions' },
    { icon: StickyNote, label: 'Notes', path: '/notes' },
    { icon: UploadIcon, label: 'New PDF', path: '/upload' },
  ];

  return (
    <div className="h-screen flex" style={{ backgroundColor: '#FFE8D6' }}>
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`fixed lg:static inset-y-0 left-0 z-50 w-64 transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 transition-transform duration-300 ease-in-out`}
        style={{ backgroundColor: '#DDBEA9' }}>
        <div className="flex flex-col h-full">
          {/* Logo Section */}
          <div className="p-6 border-b" style={{ borderColor: '#B7B7A4' }}>
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl" style={{ backgroundColor: '#CB997E' }}>
                <BookOpen className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold" style={{ color: '#6B705C' }}>Lumina IQ</h1>
                <p className="text-xs font-medium" style={{ color: '#A5A58D' }}>AI Learning Assistant</p>
              </div>
            </div>
            {/* Mobile Close Button */}
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden absolute top-4 right-4 p-2 rounded-lg hover:bg-black hover:bg-opacity-10 transition-colors"
            >
              <Menu className="h-5 w-5" style={{ color: '#6B705C' }} />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            {navigationItems.map((item) => (
              <button
                key={item.path}
                onClick={() => {
                  router.push(item.path);
                  setSidebarOpen(false);
                }}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 group ${item.active
                    ? 'shadow-lg transform scale-105'
                    : 'hover:shadow-md hover:transform hover:scale-105'
                  }`}
                style={{
                  backgroundColor: item.active ? '#CB997E' : 'transparent',
                  color: item.active ? 'white' : '#6B705C'
                }}
                onMouseEnter={(e) => {
                  if (!item.active) {
                    e.currentTarget.style.backgroundColor = 'rgba(203, 153, 126, 0.1)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!item.active) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }
                }}
              >
                <item.icon className="h-5 w-5" />
                <span className="font-medium">{item.label}</span>
              </button>
            ))}
          </nav>

          {/* User Section */}
          <div className="p-4 border-t" style={{ borderColor: '#B7B7A4' }}>
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 rounded-lg" style={{ backgroundColor: '#A5A58D' }}>
                <User className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate" style={{ color: '#6B705C' }}>
                  {user?.username}
                </p>
                <p className="text-xs" style={{ color: '#A5A58D' }}>Logged in</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="w-full flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 hover:shadow-md"
              style={{ backgroundColor: '#CB997E', color: 'white' }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#B8876B';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#CB997E';
              }}
            >
              <LogOut className="h-4 w-4" />
              <span className="text-sm font-medium">Logout</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row h-full min-h-0">
        {/* Mobile Header */}
        <div className="flex-shrink-0 lg:hidden p-4 border-b flex items-center justify-between" style={{ borderColor: '#DDBEA9' }}>
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-black hover:bg-opacity-10 transition-colors"
          >
            <Menu className="h-6 w-6" style={{ color: '#6B705C' }} />
          </button>
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-lg" style={{ backgroundColor: '#CB997E' }}>
              <HelpCircle className="h-5 w-5 text-white" />
            </div>
            <h1 className="text-lg font-bold" style={{ color: '#6B705C' }}>Q&A Learning</h1>
          </div>
          <div></div>
        </div>

        {/* Q&A Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {generatingQuestions ? (
              <div className="text-center py-12">
                <div className="p-4 rounded-2xl w-16 h-16 mx-auto mb-4 flex items-center justify-center shadow-lg animate-pulse"
                  style={{ backgroundColor: '#CB997E' }}>
                  <Sparkles className="h-8 w-8 text-white" />
                </div>
                <h3 className="text-xl font-bold mb-2" style={{ color: '#6B705C' }}>
                  Generating Questions...
                </h3>
                <p className="max-w-md mx-auto leading-relaxed" style={{ color: '#A5A58D' }}>
                  AI is analyzing your document &quot;{pdfInfo?.filename}&quot; and creating {questionCount} comprehensive questions{questionTopic.trim() ? ` focused on &quot;${questionTopic.trim()}&quot;` : ' based on the entire content'}.
                </p>
                <div className="mt-4 text-sm" style={{ color: '#B7B7A4' }}>
                  This may take 30-60 seconds...
                </div>
              </div>
            ) : chapters.length === 0 ? (
              <div className="max-w-2xl mx-auto">
                <div className="text-center py-8 mb-8">
                  <div className="p-4 rounded-2xl w-16 h-16 mx-auto mb-4 flex items-center justify-center shadow-lg"
                    style={{ backgroundColor: '#CB997E' }}>
                    <Sparkles className="h-8 w-8 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold mb-2" style={{ color: '#6B705C' }}>
                    Ready to Generate Questions
                  </h3>
                  <p className="max-w-md mx-auto leading-relaxed" style={{ color: '#A5A58D' }}>
                    Your document &quot;{pdfInfo?.filename}&quot; is loaded and ready. Customize your learning experience below.
                  </p>
                </div>

                {/* Enhanced Form */}
                <div className="rounded-2xl p-8 shadow-lg border-2 mb-8"
                  style={{ backgroundColor: '#DDBEA9', borderColor: '#B7B7A4' }}>
                  <div className="grid md:grid-cols-2 gap-6 mb-6">
                    {/* Topic Input */}
                    <div>
                      <label htmlFor="questionTopic" className="block text-sm font-semibold mb-3" style={{ color: '#6B705C' }}>
                        <Target className="h-4 w-4 inline mr-2" />
                        Specific Topic (Optional)
                      </label>
                      <input
                        id="questionTopic"
                        type="text"
                        value={questionTopic}
                        onChange={(e) => setQuestionTopic(e.target.value)}
                        placeholder="e.g., 'machine learning', 'chapter 3', 'data structures'..."
                        className="w-full px-4 py-3 rounded-xl border-2 transition-all duration-200 text-sm font-medium"
                        style={{
                          backgroundColor: '#FFE8D6',
                          borderColor: '#B7B7A4',
                          color: '#6B705C'
                        }}
                        onFocus={(e) => {
                          e.target.style.borderColor = '#CB997E';
                          e.target.style.boxShadow = '0 0 0 3px rgba(203, 153, 126, 0.1)';
                        }}
                        onBlur={(e) => {
                          e.target.style.borderColor = '#B7B7A4';
                          e.target.style.boxShadow = 'none';
                        }}
                      />
                      <p className="text-xs mt-2" style={{ color: '#A5A58D' }}>
                        Leave empty for questions about the entire document
                      </p>
                    </div>

                    {/* Question Count */}
                    <div>
                      <label htmlFor="questionCount" className="block text-sm font-semibold mb-3" style={{ color: '#6B705C' }}>
                        <Hash className="h-4 w-4 inline mr-2" />
                        Number of Questions
                      </label>
                      <select
                        id="questionCount"
                        value={questionCount}
                        onChange={(e) => setQuestionCount(Number(e.target.value))}
                        className="w-full px-4 py-3 rounded-xl border-2 transition-all duration-200 text-sm font-medium"
                        style={{
                          backgroundColor: '#FFE8D6',
                          borderColor: '#B7B7A4',
                          color: '#6B705C'
                        }}
                        onFocus={(e) => {
                          e.target.style.borderColor = '#CB997E';
                          e.target.style.boxShadow = '0 0 0 3px rgba(203, 153, 126, 0.1)';
                        }}
                        onBlur={(e) => {
                          e.target.style.borderColor = '#B7B7A4';
                          e.target.style.boxShadow = 'none';
                        }}
                      >
                        <option value={10}>10 Questions</option>
                        <option value={15}>15 Questions</option>
                        <option value={20}>20 Questions</option>
                        <option value={25}>25 Questions</option>
                        <option value={30}>30 Questions</option>
                        <option value={40}>40 Questions</option>
                        <option value={50}>50 Questions</option>
                      </select>
                      <p className="text-xs mt-2" style={{ color: '#A5A58D' }}>
                        More questions = deeper coverage
                      </p>
                    </div>
                  </div>

                  {/* Preview Box */}
                  <div className="rounded-xl p-4 mb-6 border-2"
                    style={{ backgroundColor: '#FFE8D6', borderColor: '#CB997E' }}>
                    <p className="text-sm font-semibold mb-2" style={{ color: '#6B705C' }}>
                      <Zap className="h-4 w-4 inline mr-2" />
                      What you'll get:
                    </p>
                    <ul className="text-sm space-y-1" style={{ color: '#A5A58D' }}>
                      <li className="flex items-center">
                        <CheckCircle2 className="h-3 w-3 mr-2" style={{ color: '#CB997E' }} />
                        {questionCount} comprehensive questions {questionTopic.trim() ? `focused on "${questionTopic.trim()}"` : 'covering the entire document'}
                      </li>
                      <li className="flex items-center">
                        <CheckCircle2 className="h-3 w-3 mr-2" style={{ color: '#CB997E' }} />
                        Questions about key concepts, definitions, and examples
                      </li>
                      <li className="flex items-center">
                        <CheckCircle2 className="h-3 w-3 mr-2" style={{ color: '#CB997E' }} />
                        Critical thinking questions for deeper understanding
                      </li>
                      <li className="flex items-center">
                        <CheckCircle2 className="h-3 w-3 mr-2" style={{ color: '#CB997E' }} />
                        Click any question to get detailed AI-powered answers
                      </li>
                    </ul>
                  </div>

                  {/* Generate Button */}
                  <button
                    onClick={() => generateChapterQuestions()}
                    className="w-full px-8 py-4 rounded-xl font-semibold transition-all duration-300 shadow-lg hover:shadow-xl transform hover:scale-105 flex items-center justify-center space-x-3"
                    style={{ backgroundColor: '#CB997E', color: 'white' }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = '#B8876B';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = '#CB997E';
                    }}
                  >
                    <Sparkles className="h-5 w-5" />
                    <span>Generate {questionCount} Questions{questionTopic.trim() ? ` about "${questionTopic.trim()}"` : ''}</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {chapters.map((chapter) => (
                  <div key={chapter.id} className="rounded-2xl shadow-lg border-2 overflow-hidden transition-all duration-300 hover:shadow-xl"
                    style={{ backgroundColor: '#DDBEA9', borderColor: '#B7B7A4' }}>
                    <button
                      onClick={() => toggleChapter(chapter.id)}
                      className="w-full flex items-center justify-between p-6 transition-all duration-200"
                      style={{
                        backgroundColor: chapter.expanded ? '#CB997E' : 'transparent',
                        color: chapter.expanded ? 'white' : '#6B705C'
                      }}
                      onMouseEnter={(e) => {
                        if (!chapter.expanded) {
                          e.currentTarget.style.backgroundColor = 'rgba(203, 153, 126, 0.1)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!chapter.expanded) {
                          e.currentTarget.style.backgroundColor = 'transparent';
                        }
                      }}
                    >
                      <div className="flex items-center space-x-4">
                        <div className="p-3 rounded-xl"
                          style={{ backgroundColor: chapter.expanded ? 'rgba(255, 255, 255, 0.2)' : '#CB997E' }}>
                          <BookOpen className="h-5 w-5 text-white" />
                        </div>
                        <div className="text-left">
                          <h3 className="text-lg font-bold">{chapter.title}</h3>
                          <p className="text-sm opacity-80">
                            {chapter.questions.length} questions available
                          </p>
                        </div>
                        <span className="px-3 py-1 rounded-full text-xs font-semibold"
                          style={{
                            backgroundColor: chapter.expanded ? 'rgba(255, 255, 255, 0.2)' : '#FFE8D6',
                            color: chapter.expanded ? 'white' : '#6B705C'
                          }}>
                          {chapter.questions.length}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        {chapter.loading && (
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2"
                            style={{ borderColor: chapter.expanded ? 'white' : '#CB997E' }}></div>
                        )}
                        {chapter.expanded ? (
                          <ChevronDown className="h-6 w-6" />
                        ) : (
                          <ChevronRight className="h-6 w-6" />
                        )}
                      </div>
                    </button>

                    {chapter.expanded && (
                      <div className="p-6 space-y-4" style={{ backgroundColor: '#FFE8D6' }}>
                        {chapter.questions.map((question) => (
                          <div key={question.id} className="rounded-xl border-2 overflow-hidden transition-all duration-300 hover:shadow-lg"
                            style={{ backgroundColor: '#DDBEA9', borderColor: '#B7B7A4' }}>
                            <button
                              onClick={() => handleQuestionClick(chapter.id, question.id)}
                              className="w-full text-left p-5 transition-all duration-200"
                              style={{ backgroundColor: 'transparent' }}
                              disabled={question.loading}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.backgroundColor = 'rgba(203, 153, 126, 0.1)';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.backgroundColor = 'transparent';
                              }}
                            >
                              <div className="flex items-start space-x-4">
                                <div className="flex-shrink-0 mt-1">
                                  {question.loading ? (
                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2"
                                      style={{ borderColor: '#CB997E' }}></div>
                                  ) : question.answer ? (
                                    <div className="w-5 h-5 rounded-full flex items-center justify-center"
                                      style={{ backgroundColor: '#CB997E' }}>
                                      <CheckCircle2 className="h-3 w-3 text-white" />
                                    </div>
                                  ) : (
                                    <div className="w-5 h-5 rounded-full flex items-center justify-center"
                                      style={{ backgroundColor: '#A5A58D' }}>
                                      <HelpCircle className="h-3 w-3 text-white" />
                                    </div>
                                  )}
                                </div>
                                <div className="flex-1">
                                  <p className="font-semibold mb-3 leading-relaxed" style={{ color: '#6B705C' }}>
                                    {question.question}
                                  </p>
                                  {question.answer && (
                                    <div className="rounded-xl p-4 border-2"
                                      style={{ backgroundColor: '#FFE8D6', borderColor: '#CB997E' }}>
                                      <div className="prose prose-sm max-w-none">
                                        <ReactMarkdown
                                          remarkPlugins={[remarkGfm]}
                                          components={{
                                            p: ({ children }) => (
                                              <p className="leading-relaxed mb-2" style={{ color: '#6B705C' }}>{children}</p>
                                            ),
                                            pre: ({ children }) => (
                                              <div className="my-3 overflow-hidden rounded-lg">{children}</div>
                                            ),
                                            h1: ({ children }) => (
                                              <h1 className="text-lg font-bold mb-3 mt-4 first:mt-0" style={{ color: '#6B705C' }}>
                                                {children}
                                              </h1>
                                            ),
                                            h2: ({ children }) => (
                                              <h2 className="text-base font-semibold mb-2 mt-3" style={{ color: '#6B705C' }}>
                                                {children}
                                              </h2>
                                            ),
                                            h3: ({ children }) => (
                                              <h3 className="text-sm font-semibold mb-2 mt-3" style={{ color: '#A5A58D' }}>
                                                {children}
                                              </h3>
                                            ),
                                            ul: ({ children }) => (
                                              <ul className="list-disc list-inside space-y-1 mb-2 ml-2" style={{ color: '#6B705C' }}>
                                                {children}
                                              </ul>
                                            ),
                                            ol: ({ children }) => (
                                              <ol className="list-decimal list-inside space-y-1 mb-2 ml-2" style={{ color: '#6B705C' }}>
                                                {children}
                                              </ol>
                                            ),
                                            li: ({ children }) => (
                                              <li className="text-sm" style={{ color: '#6B705C' }}>{children}</li>
                                            ),
                                            blockquote: ({ children }) => (
                                              <blockquote className="border-l-4 pl-3 italic py-2 rounded-r mb-2"
                                                style={{
                                                  borderColor: '#CB997E',
                                                  backgroundColor: '#DDBEA9',
                                                  color: '#A5A58D'
                                                }}>
                                                {children}
                                              </blockquote>
                                            ),
                                            code: ({ className, children, ...props }: any) => {
                                              const match = /language-(\w+)/.exec(className || '');
                                              const language = match ? match[1] : '';
                                              const isInline = !className || !match;

                                              return !isInline ? (
                                                <div className="relative my-3 group">
                                                  <div className="flex items-center justify-between bg-gray-800 text-gray-300 px-3 py-2 rounded-t-lg text-xs">
                                                    <span className="font-medium">
                                                      {language ? language.toUpperCase() : 'CODE'}
                                                    </span>
                                                    <button
                                                      onClick={() => navigator.clipboard?.writeText(String(children))}
                                                      className="flex items-center space-x-1 px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs transition-colors opacity-0 group-hover:opacity-100"
                                                      title="Copy code"
                                                    >
                                                      <Copy className="h-3 w-3" />
                                                      <span>Copy</span>
                                                    </button>
                                                  </div>
                                                  <SyntaxHighlighter
                                                    language={language || 'text'}
                                                    style={vscDarkPlus}
                                                    customStyle={{
                                                      margin: 0,
                                                      borderRadius: '0 0 0.5rem 0.5rem',
                                                      fontSize: '0.75rem',
                                                      lineHeight: '1.4'
                                                    }}
                                                    showLineNumbers={true}
                                                    wrapLines={true}
                                                  >
                                                    {String(children).replace(/\n$/, '')}
                                                  </SyntaxHighlighter>
                                                </div>
                                              ) : (
                                                <code className="bg-gray-100 text-gray-800 px-2 py-1 rounded text-xs font-mono border" {...props}>
                                                  {children}
                                                </code>
                                              );
                                            },
                                            strong: ({ children }) => (
                                              <strong className="font-semibold" style={{ color: '#6B705C' }}>{children}</strong>
                                            ),
                                            em: ({ children }) => (
                                              <em className="italic" style={{ color: '#A5A58D' }}>{children}</em>
                                            ),
                                            table: ({ children }) => (
                                              <div className="overflow-x-auto mb-2">
                                                <table className="min-w-full border rounded text-xs"
                                                  style={{ borderColor: '#B7B7A4' }}>
                                                  {children}
                                                </table>
                                              </div>
                                            ),
                                            thead: ({ children }) => (
                                              <thead style={{ backgroundColor: '#DDBEA9' }}>
                                                {children}
                                              </thead>
                                            ),
                                            th: ({ children }) => (
                                              <th className="border px-2 py-1 text-left font-semibold"
                                                style={{ borderColor: '#B7B7A4', color: '#6B705C' }}>
                                                {children}
                                              </th>
                                            ),
                                            td: ({ children }) => (
                                              <td className="border px-2 py-1"
                                                style={{ borderColor: '#B7B7A4', color: '#6B705C', backgroundColor: 'transparent' }}>
                                                {children}
                                              </td>
                                            ),
                                            tbody: ({ children }) => (
                                              <tbody style={{ backgroundColor: 'transparent' }}>
                                                {children}
                                              </tbody>
                                            ),
                                            tr: ({ children }) => (
                                              <tr style={{ color: '#6B705C' }}>
                                                {children}
                                              </tr>
                                            ),
                                          }}
                                        >
                                          {question.answer}
                                        </ReactMarkdown>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Information Sidebar */}
        {pdfInfo && (
          <div className="hidden lg:block w-80 border-l p-6 overflow-y-auto"
            style={{ backgroundColor: '#DDBEA9', borderColor: '#B7B7A4' }}>
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-bold mb-4 flex items-center" style={{ color: '#6B705C' }}>
                  <FileText className="h-5 w-5 mr-2" style={{ color: '#CB997E' }} />
                  Document Info
                </h3>
                <div className="space-y-3">
                  <div className="rounded-xl p-4 border-2"
                    style={{ backgroundColor: '#FFE8D6', borderColor: '#B7B7A4' }}>
                    <label className="text-xs font-bold uppercase tracking-wide" style={{ color: '#A5A58D' }}>
                      Filename
                    </label>
                    <p className="text-sm font-semibold mt-1 break-words" style={{ color: '#6B705C' }}>
                      {pdfInfo.filename}
                    </p>
                  </div>

                  <div className="rounded-xl p-4 border-2"
                    style={{ backgroundColor: '#FFE8D6', borderColor: '#B7B7A4' }}>
                    <label className="text-xs font-bold uppercase tracking-wide" style={{ color: '#A5A58D' }}>
                      File Size
                    </label>
                    <p className="text-sm font-semibold mt-1" style={{ color: '#6B705C' }}>
                      {formatFileSize(pdfInfo.metadata?.file_size || 0)}
                    </p>
                  </div>

                  <div className="rounded-xl p-4 border-2"
                    style={{ backgroundColor: '#FFE8D6', borderColor: '#B7B7A4' }}>
                    <label className="text-xs font-bold uppercase tracking-wide" style={{ color: '#A5A58D' }}>
                      Pages
                    </label>
                    <p className="text-sm font-semibold mt-1" style={{ color: '#6B705C' }}>
                      {pdfInfo.metadata?.pages || 'Unknown'}
                    </p>
                  </div>

                  <div className="rounded-xl p-4 border-2"
                    style={{ backgroundColor: '#FFE8D6', borderColor: '#B7B7A4' }}>
                    <label className="text-xs font-bold uppercase tracking-wide" style={{ color: '#A5A58D' }}>
                      Selected Date
                    </label>
                    <p className="text-sm font-semibold mt-1" style={{ color: '#6B705C' }}>
                      {formatDate(pdfInfo.selected_at || 'Unknown')}
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-bold mb-4 flex items-center" style={{ color: '#6B705C' }}>
                  <Settings className="h-5 w-5 mr-2" style={{ color: '#CB997E' }} />
                  Quick Actions
                </h3>
                <div className="space-y-3">
                  <button
                    onClick={testAIConnection}
                    disabled={testingAI}
                    className="w-full px-4 py-3 rounded-xl font-semibold transition-all duration-200 shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ backgroundColor: '#CB997E', color: 'white' }}
                    onMouseEnter={(e) => {
                      if (!testingAI) {
                        e.currentTarget.style.backgroundColor = '#B8876B';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!testingAI) {
                        e.currentTarget.style.backgroundColor = '#CB997E';
                      }
                    }}
                  >
                    {testingAI ? (
                      <div className="flex items-center justify-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        <span>Testing...</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center space-x-2">
                        <Zap className="h-4 w-4" />
                        <span>Test AI Connection</span>
                      </div>
                    )}
                  </button>

                  <button
                    onClick={() => generateChapterQuestions()}
                    disabled={generatingQuestions}
                    className="w-full px-4 py-3 rounded-xl font-semibold transition-all duration-200 shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ backgroundColor: '#A5A58D', color: 'white' }}
                    onMouseEnter={(e) => {
                      if (!generatingQuestions) {
                        e.currentTarget.style.backgroundColor = '#94947A';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!generatingQuestions) {
                        e.currentTarget.style.backgroundColor = '#A5A58D';
                      }
                    }}
                  >
                    {generatingQuestions ? (
                      <div className="flex items-center justify-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        <span>Generating...</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center space-x-2">
                        <Sparkles className="h-4 w-4" />
                        <span>Regenerate Questions</span>
                      </div>
                    )}
                  </button>
                </div>
              </div>

              {chapters.length > 0 && (
                <div>
                  <h3 className="text-lg font-bold mb-4 flex items-center" style={{ color: '#6B705C' }}>
                    <Target className="h-5 w-5 mr-2" style={{ color: '#CB997E' }} />
                    Statistics
                  </h3>
                  <div className="space-y-3">
                    <div className="rounded-xl p-4 text-white shadow-lg"
                      style={{ backgroundColor: '#CB997E' }}>
                      <label className="text-xs font-bold uppercase tracking-wide opacity-90">
                        Total Chapters
                      </label>
                      <p className="text-lg font-bold mt-1">{chapters.length}</p>
                    </div>

                    <div className="rounded-xl p-4 text-white shadow-lg"
                      style={{ backgroundColor: '#A5A58D' }}>
                      <label className="text-xs font-bold uppercase tracking-wide opacity-90">
                        Questions Generated
                      </label>
                      <p className="text-lg font-bold mt-1">
                        {chapters.reduce((total, chapter) => total + chapter.questions.length, 0)}
                      </p>
                      <p className="text-xs opacity-80">across {chapters.length} chapters</p>
                    </div>

                    <div className="rounded-xl p-4 border-2"
                      style={{ backgroundColor: '#FFE8D6', borderColor: '#B7B7A4' }}>
                      <label className="text-xs font-bold uppercase tracking-wide" style={{ color: '#A5A58D' }}>
                        Answered Questions
                      </label>
                      <p className="text-lg font-bold mt-1" style={{ color: '#6B705C' }}>
                        {chapters.reduce((total, chapter) =>
                          total + chapter.questions.filter(q => q.answer).length, 0
                        )}
                      </p>
                      <p className="text-xs" style={{ color: '#A5A58D' }}>
                        out of {chapters.reduce((total, chapter) => total + chapter.questions.length, 0)} total
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}