import React, { useState } from 'react';
import Home from './pages/Home';
import SearchBar from './components/SearchBar';
import { generatePodcast } from './api/apiClient';
import './index.css';

function App() {
    const [topic, setTopic] = useState('');
    const [voice, setVoice] = useState(null);
    const [data, setData] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [activeView, setActiveView] = useState('summary');

    const handleGenerate = async (topicVal, voiceVal, showView = 'summary') => {
        setIsLoading(true);
        setError(null);
        setData(null);
        try {
            const result = await generatePodcast(topicVal, voiceVal || undefined);
            if (result.status === 'error') {
                setError(result.error);
            } else {
                setData(result);
                setActiveView(showView);
            }
        } catch (err) {
            setError(typeof err === 'string' ? err : err?.message || 'Failed to generate.');
        } finally {
            setIsLoading(false);
        }
    };

    const onSearch = () => {
        if (!isLoading) handleGenerate(topic, voice, 'summary');
    };

    return (
        <div className="app-container">
            <div className="app-shell">
                <div className="app-left">
                    <header className="app-header">
                        <p className="hero-label">Smart Finance Podcast</p>
                        <h1 className="hero-title">
                            Podcasts that inspire
                            <br />
                            to grow
                        </h1>
                        <p className="hero-description">
                            From verified financial data to ready-to-listen briefings — an autonomous research agent
                            generating accurate market podcasts.
                        </p>
                    </header>
                    <main>
                        <Home
                            voice={voice}
                            onVoiceChange={setVoice}
                            data={data}
                            isLoading={isLoading}
                            error={error}
                            activeView={activeView}
                            onSummaryClick={() => {
                                if (data) setActiveView('summary');
                                else if (!isLoading) handleGenerate(topic, voice, 'summary');
                            }}
                            onListenClick={() => {
                                if (data) setActiveView('audio');
                                else if (!isLoading) handleGenerate(topic, voice, 'audio');
                            }}
                        />
                    </main>
                    <footer className="app-footer">
                        <p>
                            © {new Date().getFullYear()} Smart Finance Podcast. All data is verified for yesterday&apos;s
                            closing.
                        </p>
                    </footer>
                </div>
                <aside className="app-right">
                    <div className="hero-image-frame">
                        <img
                            src="/hero-mic.png"
                            alt="Finance podcast microphone with digital market dashboard"
                            className="hero-image"
                            onError={(e) => {
                                e.target.onerror = null;
                                e.target.src = '/hero-placeholder.svg';
                            }}
                        />
                    </div>
                    <div className="app-right-search">
                        <SearchBar
                            topic={topic}
                            onTopicChange={setTopic}
                            onSearch={onSearch}
                            isLoading={isLoading}
                        />
                    </div>
                </aside>
            </div>
        </div>
    );
}

export default App;
