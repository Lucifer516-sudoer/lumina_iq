'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { chatApi, pdfApi, ChatHistoryItem, PDFSessionInfo } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  Send,
  BookOpen,
  LogOut,
  FileText,
  Calendar,
  User,
  Hash,
  HardDrive,
  Upload as UploadIcon,
  MessageCircle,
  Bot,
  Sparkles,
  Copy,
  Check,
  HelpCircle,
  Brain,
  StickyNote,
  Menu,
  X
} from 'lucide-react';

export default function ChatPage() {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState<ChatHistoryItem[]>([]);
  const [pdfInfo, setPdfInfo] = useState<PDFSessionInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const { logout, user } = useAuth();
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadInitialData = useCallback(async () => {
    try {
      const [historyData, pdfData] = await Promise.all([
        chatApi.getChatHistory(),
        pdfApi.getPDFInfo()
      ]);

      setChatHistory(historyData?.history || []);
      setPdfInfo(pdfData);
    } catch (error) {
      console.error('Failed to load initial data:', error);
      // If no PDF is uploaded, redirect to upload page
      router.push('/upload');
    } finally {
      setInitialLoading(false);
    }
  }, [router]);

  useEffect(() => {
    loadInitialData();

    // Cleanup function to clear chat history when component unmounts
    return () => {
      clearChatHistoryOnExit();
    };
  }, [loadInitialData]);

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const clearChatHistoryOnExit = async () => {
    try {
      await chatApi.clearChatHistory();
      console.log('Chat history cleared on exit');
    } catch (error) {
      console.error('Failed to clear chat history on exit:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || loading) return;

    const userMessage = message.trim();
    setMessage('');
    setLoading(true);

    try {
      const response = await chatApi.sendMessage(userMessage);
      
      // Add the new message to chat history
      const newMessage: ChatHistoryItem = {
        user: userMessage,
        assistant: response.response,
        timestamp: response.timestamp
      };
      
      setChatHistory(prev => [...prev, newMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    // Clear chat history before logging out
    await clearChatHistoryOnExit();
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

  const copyToClipboard = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  if (initialLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#FFE8D6' }}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{ borderColor: '#CB997E' }}></div>
          <p style={{ color: '#6B705C' }}>Loading your learning session...</p>
        </div>
      </div>
    );
  }

  const navigationItems = [
    { icon: MessageCircle, label: 'Chat', path: '/chat', active: true },
    { icon: HelpCircle, label: 'Q&A Generation', path: '/qa' },
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
              <X className="h-5 w-5" style={{ color: '#6B705C' }} />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            {navigationItems.map((item) => (
              <button
                key={item.path}
                onClick={async () => {
                  // Clear chat history when navigating away from chat page
                  if (item.path !== '/chat') {
                    await clearChatHistoryOnExit();
                  }
                  router.push(item.path);
                  setSidebarOpen(false);
                }}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
                  item.active
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
              <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ backgroundColor: '#CB997E' }}>
                <User className="h-5 w-5 text-white" />
              </div>
              <div>
                <p className="font-medium" style={{ color: '#6B705C' }}>{user?.username}</p>
                <p className="text-xs" style={{ color: '#A5A58D' }}>Learning Mode</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="w-full flex items-center space-x-3 px-4 py-2 rounded-lg transition-all duration-200 hover:shadow-md"
              style={{ color: '#6B705C' }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(107, 112, 92, 0.1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              <LogOut className="h-4 w-4" />
              <span className="font-medium">Logout</span>
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
              <MessageCircle className="h-5 w-5 text-white" />
            </div>
            <h1 className="text-lg font-bold" style={{ color: '#6B705C' }}>Chat</h1>
          </div>
          <div></div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col h-full">
          {/* Chat Header - Fixed */}
          <div className="flex-shrink-0 hidden lg:block p-6 border-b" style={{ borderColor: '#DDBEA9' }}>
            <div className="flex items-center space-x-3">
              <div className="p-3 rounded-xl" style={{ backgroundColor: '#CB997E' }}>
                <MessageCircle className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold" style={{ color: '#6B705C' }}>Chat with AI</h1>
                {pdfInfo && (
                  <p className="text-sm font-medium" style={{ color: '#A5A58D' }}>
                    Learning from: {pdfInfo.filename}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Messages - Scrollable Content Area */}
          <div className="flex-1 overflow-y-auto px-4 lg:px-6 py-6 space-y-6 min-h-0"
               style={{
                 scrollbarWidth: 'thin',
                 scrollbarColor: '#CB997E #DDBEA9'
               }}>
            {chatHistory.length === 0 ? (
              <div className="text-center py-12">
                <div className="p-4 rounded-2xl w-16 h-16 mx-auto mb-6 flex items-center justify-center shadow-lg animate-pulse"
                     style={{ backgroundColor: '#CB997E' }}>
                  <Sparkles className="h-8 w-8 text-white" />
                </div>
                <h3 className="text-2xl font-bold mb-3" style={{ color: '#6B705C' }}>
                  Start Your Learning Journey
                </h3>
                <p className="max-w-md mx-auto leading-relaxed mb-8" style={{ color: '#A5A58D' }}>
                  Ask any question about your selected PDF. I&apos;m here to help you understand and learn from the content.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-lg mx-auto">
                  <div className="rounded-xl p-4 border-2 transition-all duration-200 hover:shadow-lg hover:scale-105"
                       style={{
                         backgroundColor: 'rgba(255, 232, 214, 0.8)',
                         borderColor: '#DDBEA9'
                       }}>
                    <h4 className="font-semibold mb-2" style={{ color: '#6B705C' }}>💡 Ask for explanations</h4>
                    <p className="text-sm" style={{ color: '#A5A58D' }}>&quot;Explain the main concepts&quot;</p>
                  </div>
                  <div className="rounded-xl p-4 border-2 transition-all duration-200 hover:shadow-lg hover:scale-105"
                       style={{
                         backgroundColor: 'rgba(255, 232, 214, 0.8)',
                         borderColor: '#DDBEA9'
                       }}>
                    <h4 className="font-semibold mb-2" style={{ color: '#6B705C' }}>🔍 Get specific details</h4>
                    <p className="text-sm" style={{ color: '#A5A58D' }}>&quot;What are the key points...&quot;</p>
                  </div>
                </div>
              </div>
            ) : (
              chatHistory.map((chat, index) => (
                <div key={index} className="space-y-4 animate-fade-in">
                  {/* User Message */}
                  <div className="flex justify-end">
                    <div className="text-white rounded-2xl rounded-tr-md px-5 py-3 max-w-xs md:max-w-2xl shadow-lg transform transition-all duration-200 hover:scale-105"
                         style={{ backgroundColor: '#CB997E' }}>
                      <p className="leading-relaxed">{chat.user}</p>
                    </div>
                  </div>

                  {/* AI Response */}
                  <div className="flex items-start space-x-3">
                    <div className="p-2 rounded-lg flex-shrink-0 shadow-lg"
                         style={{ backgroundColor: '#A5A58D' }}>
                      <Bot className="h-4 w-4 text-white" />
                    </div>
                    <div className="rounded-2xl rounded-tl-md px-5 py-4 shadow-xl border-2 flex-1 transform transition-all duration-200 hover:shadow-2xl"
                         style={{
                           backgroundColor: 'rgba(255, 232, 214, 0.9)',
                           borderColor: '#DDBEA9'
                         }}>
                      <div className="prose prose-sm max-w-none">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({ children }) => (
                              <p className="leading-relaxed mb-2" style={{ color: '#6B705C' }}>{children}</p>
                            ),
                            pre: ({ children }) => (
                              <div className="my-4 overflow-hidden rounded-lg">{children}</div>
                            ),
                            code: ({ className, children, ref, ...rest }) => {
                              const match = /language-(\w+)/.exec(className || '');
                              const language = match ? match[1] : '';
                              const isInline = !className || !match;

                              return !isInline ? (
                                <div className="relative my-4 group">
                                  <div className="flex items-center justify-between bg-gray-800 text-gray-300 px-4 py-2 rounded-t-lg text-sm">
                                    <span className="font-medium">
                                      {language ? language.toUpperCase() : 'CODE'}
                                    </span>
                                    <button
                                      onClick={() => copyToClipboard(String(children), index)}
                                      className="flex items-center space-x-1 px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs transition-colors opacity-0 group-hover:opacity-100"
                                      title="Copy code"
                                    >
                                      {copiedIndex === index ? (
                                        <>
                                          <Check className="h-3 w-3 text-green-400" />
                                          <span className="text-green-400">Copied!</span>
                                        </>
                                      ) : (
                                        <>
                                          <Copy className="h-3 w-3" />
                                          <span>Copy</span>
                                        </>
                                      )}
                                    </button>
                                  </div>
                                  <SyntaxHighlighter
                                    language={language || 'text'}
                                    style={vscDarkPlus as any}
                                    customStyle={{
                                      margin: 0,
                                      borderRadius: '0 0 0.5rem 0.5rem',
                                      fontSize: '0.875rem',
                                      lineHeight: '1.5'
                                    }}
                                    showLineNumbers={true}
                                    wrapLines={true}
                                    {...rest}
                                  >
                                    {String(children).replace(/\n$/, '')}
                                  </SyntaxHighlighter>
                                </div>
                              ) : (
                                <code className="bg-gray-100 text-gray-800 px-2 py-1 rounded text-sm font-mono border" {...rest}>
                                  {children}
                                </code>
                              );
                            },
                            h1: ({ children }) => (
                              <h1 className="text-lg font-bold mb-2 border-b pb-1"
                                  style={{ color: '#6B705C', borderColor: '#DDBEA9' }}>
                                {children}
                              </h1>
                            ),
                            h2: ({ children }) => (
                              <h2 className="text-base font-semibold mb-2 mt-3" style={{ color: '#6B705C' }}>
                                {children}
                              </h2>
                            ),
                            h3: ({ children }) => (
                              <h3 className="text-sm font-semibold mb-1 mt-2" style={{ color: '#A5A58D' }}>
                                {children}
                              </h3>
                            ),
                            ul: ({ children }) => (
                              <ul className="list-disc list-inside space-y-0.5 mb-2 ml-2" style={{ color: '#6B705C' }}>
                                {children}
                              </ul>
                            ),
                            ol: ({ children }) => (
                              <ol className="list-decimal list-inside space-y-0.5 mb-2 ml-2" style={{ color: '#6B705C' }}>
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
                                            backgroundColor: 'rgba(203, 153, 126, 0.1)',
                                            color: '#A5A58D'
                                          }}>
                                {children}
                              </blockquote>
                            ),
                            strong: ({ children }) => (
                              <strong className="font-semibold" style={{ color: '#6B705C' }}>{children}</strong>
                            ),
                            em: ({ children }) => (
                              <em className="italic" style={{ color: '#A5A58D' }}>{children}</em>
                            ),
                          }}
                        >
                          {chat.assistant}
                        </ReactMarkdown>
                      </div>
                      <div className="flex items-center justify-between mt-3 pt-2 border-t"
                           style={{ borderColor: '#DDBEA9' }}>
                        <p className="text-xs" style={{ color: '#A5A58D' }}>
                          {formatDate(chat.timestamp)}
                        </p>
                        <button
                          onClick={() => copyToClipboard(chat.assistant, index + 1000)}
                          className="flex items-center space-x-1 text-xs transition-colors hover:scale-105 transform duration-200"
                          style={{ color: '#A5A58D' }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.color = '#CB997E';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.color = '#A5A58D';
                          }}
                        >
                          {copiedIndex === index + 1000 ? (
                            <>
                              <Check className="h-3 w-3" />
                              <span>Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="h-3 w-3" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}

            {loading && (
              <div className="flex items-start space-x-3 animate-fade-in">
                <div className="p-2 rounded-lg flex-shrink-0 shadow-lg"
                     style={{ backgroundColor: '#A5A58D' }}>
                  <Bot className="h-4 w-4 text-white" />
                </div>
                <div className="rounded-2xl rounded-tl-md px-5 py-4 shadow-xl border-2"
                     style={{
                       backgroundColor: 'rgba(255, 232, 214, 0.9)',
                       borderColor: '#DDBEA9'
                     }}>
                  <div className="flex items-center space-x-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 rounded-full animate-bounce"
                           style={{ backgroundColor: '#CB997E' }}></div>
                      <div className="w-2 h-2 rounded-full animate-bounce"
                           style={{ backgroundColor: '#A5A58D', animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 rounded-full animate-bounce"
                           style={{ backgroundColor: '#6B705C', animationDelay: '0.2s' }}></div>
                    </div>
                    <span className="text-sm font-medium" style={{ color: '#6B705C' }}>AI is thinking...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Message Input - Fixed at Bottom */}
          <div className="flex-shrink-0 border-t p-4 lg:p-6"
               style={{
                 borderColor: '#DDBEA9',
                 backgroundColor: 'rgba(221, 190, 169, 0.3)'
               }}>
            <form onSubmit={handleSendMessage} className="flex space-x-3 max-w-4xl mx-auto">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Ask a question about your PDF..."
                  className="w-full border-2 rounded-xl px-4 py-3 pr-12 transition-all duration-200 shadow-md focus:shadow-lg font-medium"
                  style={{
                    backgroundColor: '#FFE8D6',
                    borderColor: '#DDBEA9',
                    color: '#6B705C'
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = '#CB997E';
                    e.target.style.transform = 'scale(1.02)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = '#DDBEA9';
                    e.target.style.transform = 'scale(1)';
                  }}
                  disabled={loading}
                />
                <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
                  <MessageCircle className="h-4 w-4" style={{ color: '#A5A58D' }} />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading || !message.trim()}
                className="text-white px-6 py-3 rounded-xl font-medium transition-all duration-200 shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2"
                style={{
                  backgroundColor: '#CB997E',
                  // focusRingColor: '#CB997E'
                }}
                onMouseEnter={(e) => {
                  if (!loading && message.trim()) {
                    e.currentTarget.style.backgroundColor = '#B8876B';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#CB997E';
                }}
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
          </div>
        </div>

        {/* PDF Metadata Panel */}
        {pdfInfo && (
          <div className="hidden lg:block w-80 border-l p-6 overflow-y-auto"
               style={{
                 borderColor: '#DDBEA9',
                 backgroundColor: 'rgba(221, 190, 169, 0.2)'
               }}>
            <div className="rounded-xl p-4 mb-6 shadow-lg"
                 style={{ backgroundColor: '#CB997E' }}>
              <h3 className="text-lg font-bold text-white mb-1 flex items-center space-x-2">
                <FileText className="h-5 w-5" />
                <span>Document Info</span>
              </h3>
              <p className="text-white text-opacity-80 text-sm">Currently learning from</p>
            </div>

            <div className="space-y-4">
              <div className="rounded-xl p-4 shadow-md border-2 transition-all duration-200 hover:shadow-lg"
                   style={{
                     backgroundColor: '#FFE8D6',
                     borderColor: '#DDBEA9'
                   }}>
                <label className="text-xs font-bold uppercase tracking-wide"
                       style={{ color: '#A5A58D' }}>Filename</label>
                <p className="text-sm font-semibold break-words mt-2"
                   style={{ color: '#6B705C' }}>{pdfInfo.filename}</p>
              </div>

              <div className="rounded-xl p-4 shadow-md border-2 transition-all duration-200 hover:shadow-lg"
                   style={{
                     backgroundColor: '#FFE8D6',
                     borderColor: '#DDBEA9'
                   }}>
                <label className="text-xs font-bold uppercase tracking-wide"
                       style={{ color: '#A5A58D' }}>Title</label>
                <p className="text-sm font-semibold mt-2"
                   style={{ color: '#6B705C' }}>{pdfInfo.metadata.title}</p>
              </div>

              <div className="rounded-xl p-4 shadow-md border-2 transition-all duration-200 hover:shadow-lg"
                   style={{
                     backgroundColor: '#FFE8D6',
                     borderColor: '#DDBEA9'
                   }}>
                <label className="text-xs font-bold uppercase tracking-wide flex items-center space-x-1"
                       style={{ color: '#A5A58D' }}>
                  <User className="h-3 w-3" />
                  <span>Author</span>
                </label>
                <p className="text-sm font-semibold mt-2"
                   style={{ color: '#6B705C' }}>{pdfInfo.metadata.author}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl p-3 shadow-md border-2 transition-all duration-200 hover:shadow-lg"
                     style={{
                       backgroundColor: '#FFE8D6',
                       borderColor: '#DDBEA9'
                     }}>
                  <label className="text-xs font-bold uppercase tracking-wide flex items-center space-x-1"
                         style={{ color: '#A5A58D' }}>
                    <Hash className="h-3 w-3" />
                    <span>Pages</span>
                  </label>
                  <p className="text-lg font-bold mt-1"
                     style={{ color: '#6B705C' }}>{pdfInfo.metadata.pages}</p>
                </div>

                <div className="rounded-xl p-3 shadow-md border-2 transition-all duration-200 hover:shadow-lg"
                     style={{
                       backgroundColor: '#FFE8D6',
                       borderColor: '#DDBEA9'
                     }}>
                  <label className="text-xs font-bold uppercase tracking-wide flex items-center space-x-1"
                         style={{ color: '#A5A58D' }}>
                    <HardDrive className="h-3 w-3" />
                    <span>Size</span>
                  </label>
                  <p className="text-sm font-bold mt-1"
                     style={{ color: '#6B705C' }}>{formatFileSize(pdfInfo.metadata.file_size)}</p>
                </div>
              </div>

              <div className="rounded-xl p-4 shadow-md border-2 transition-all duration-200 hover:shadow-lg"
                   style={{
                     backgroundColor: '#FFE8D6',
                     borderColor: '#DDBEA9'
                   }}>
                <label className="text-xs font-bold uppercase tracking-wide flex items-center space-x-1"
                       style={{ color: '#A5A58D' }}>
                  <Calendar className="h-3 w-3" />
                  <span>Selected</span>
                </label>
                <p className="text-sm font-semibold mt-2"
                   style={{ color: '#6B705C' }}>{formatDate(pdfInfo.selected_at || pdfInfo.uploaded_at || 'Unknown')}</p>
              </div>

              <div className="rounded-xl p-4 shadow-md border-2 transition-all duration-200 hover:shadow-lg"
                   style={{
                     backgroundColor: '#FFE8D6',
                     borderColor: '#DDBEA9'
                   }}>
                <label className="text-xs font-bold uppercase tracking-wide"
                       style={{ color: '#A5A58D' }}>Subject</label>
                <p className="text-sm font-semibold mt-2"
                   style={{ color: '#6B705C' }}>{pdfInfo.metadata.subject}</p>
              </div>

              <div className="rounded-xl p-4 text-white shadow-lg border-2 transition-all duration-200 hover:shadow-xl hover:scale-105"
                   style={{
                     backgroundColor: '#A5A58D',
                     borderColor: '#6B705C'
                   }}>
                <label className="text-xs font-bold text-white text-opacity-80 uppercase tracking-wide">Content Length</label>
                <p className="text-xl font-bold mt-1">{pdfInfo.text_length.toLocaleString()}</p>
                <p className="text-xs text-white text-opacity-80">characters extracted</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Custom Styles */}
      <style jsx>{`
        @keyframes fade-in {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-fade-in {
          animation: fade-in 0.3s ease-out;
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
          width: 6px;
        }

        ::-webkit-scrollbar-track {
          background: #DDBEA9;
          border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb {
          background: #CB997E;
          border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
          background: #B8876B;
        }

        /* Smooth transitions for all interactive elements */
        * {
          transition: all 0.2s ease-in-out;
        }
      `}</style>
    </div>
  );
}
