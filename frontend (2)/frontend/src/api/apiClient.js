import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const generatePodcast = async (topic, voice = null, language = "both") => {
    try {
        const payload = { name: topic, language };
        if (voice) payload.voice_agent = voice;
        const response = await apiClient.post('/generate', payload);
        return response.data;
    } catch (error) {
        console.error('API Error:', error);
        throw error.response?.data?.detail || 'Failed to generate podcast. Please try again.';
    }
};

export default apiClient;
