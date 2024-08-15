import React, { useState, useRef } from 'react';
import ParticlesComponent from './particles';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { Button, CircularProgress, TextField, Typography, Box, List, ListItem, ListItemText, Drawer, Link, IconButton } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import SendIcon from '@mui/icons-material/Send';
import DeleteIcon from '@mui/icons-material/Delete';
import YouTubeIcon from '@mui/icons-material/YouTube';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import MenuIcon from '@mui/icons-material/Menu';
import styled from 'styled-components';
import axios from 'axios';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

// Define your theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#fff',
    },
    secondary: {
      main: '#fff',
    },
    background: {
      default: '#000',
    },
    text: {
      primary: '#fff',
    },
  },
});

// Styled components
const AppContainer = styled(Box)`
  display: flex;
  height: 100vh;
  flex-direction: column;
  background-color: #000;
`;

const Sidebar = styled(Drawer)`
  width: 300px;
  flex-shrink: 0;
  & .MuiDrawer-paper {
    width: 300px;
    box-sizing: border-box;
    padding: 1rem;
    background-color: #000;
    border-right: 1px solid #fff;
  }
`;

const MainContent = styled(Box)`
  flex-grow: 1;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  background-color: #000;
`;

const Header = styled(Typography)`
  text-align: center;
  margin-bottom: 2rem;
  color: #fff;
`;

const ChatSection = styled(Box)`
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  background-color: #000;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
`;

const ConversationContainer = styled(Box)`
  flex-grow: 1;
  overflow-y: auto;
  margin-bottom: 1rem;
  background-color: #000;
`;

const Message = styled(Box)`
  max-width: 70%;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  margin-bottom: 0.5rem;
  animation: fadeIn 0.3s ease-out;
  background-color: #fff;
  color: #000;
`;

const UserMessage = styled(Message)`
  align-self: flex-end;
  margin-left: auto;
`;

const BotMessage = styled(Message)`
  align-self: flex-start;
`;

// Input Section styled component
const InputSection = styled(Box)`
  display: flex;
  gap: 1rem;
  background-color: #000;
`;

// File List styled components
const FileList = styled(List)`
  margin-top: 1rem;
  background-color: #000;
`;

const FileListItem = styled(ListItem)`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background-color: #000;
`;

// Function to render Markdown safely
const renderMarkdown = (markdownText) => {
  const html = marked(markdownText);
  const sanitizedHtml = DOMPurify.sanitize(html);
  return { __html: sanitizedHtml };
};

function App() {
  const [files, setFiles] = useState([]);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [question, setQuestion] = useState('');
  const [conversation, setConversation] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  const handleUpload = async () => {
    setIsUploading(true);
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    formData.append('youtube_url', youtubeUrl || '');

    try {
      const response = await axios.post('https://neural-chat.onrender.com/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response.status === 200) {
        setUploadedFiles([...uploadedFiles, ...response.data.uploaded_files]);
        setFiles([]);
        setYoutubeUrl('');
        alert('Content uploaded and processed successfully');
      } else {
        alert('Unexpected response from server');
      }
    } catch (error) {
      console.error('Error uploading content:', error);
      alert('Error uploading content. Please try again.');
    }
    setIsUploading(false);
  };

  const handleAsk = async () => {
    if (!question.trim()) return;

    setIsAsking(true);
    setConversation([...conversation, { type: 'user', text: question }]);

    try {
      const response = await axios.post('https://neural-chat.onrender.com/ask', { question });
      if (response.status === 200) {
        setConversation([...conversation, 
          { type: 'user', text: question },
          { type: 'bot', text: response.data.answer }
        ]);
      } else {
        setConversation([...conversation,
          { type: 'user', text: question },
          { type: 'bot', text: 'Unexpected response from server.' }
        ]);
      }
    } catch (error) {
      console.error('Error asking question:', error);
      setConversation([...conversation,
        { type: 'user', text: question },
        { type: 'bot', text: 'Sorry, an error occurred while processing your question.' }
      ]);
    }

    setQuestion('');
    setIsAsking(false);
  };

  const handleRemoveFile = (index) => {
    const newFiles = [...files];
    newFiles.splice(index, 1);
    setFiles(newFiles);
  };

  const handleRemoveUploadedFile = (index) => {
    const newUploadedFiles = [...uploadedFiles];
    newUploadedFiles.splice(index, 1);
    setUploadedFiles(newUploadedFiles);
  };

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <ThemeProvider theme={theme}>
      <AppContainer>
        <ParticlesComponent id="particles" />
        <IconButton
          aria-label="toggle sidebar"
          onClick={toggleSidebar}
          sx={{ position: 'absolute', top: 8, left: 8, zIndex: 1, color: '#fff' }} // Set color to white
        >
          <MenuIcon />
        </IconButton>
        <Sidebar variant="temporary" open={sidebarOpen} onClose={toggleSidebar}>
          <Typography variant="h6" gutterBottom>
            File Management
          </Typography>
          <input
            type="file"
            multiple
            onChange={handleFileChange}
            style={{ display: 'none' }}
            ref={fileInputRef}
          />
          <Button
            variant="contained"
            startIcon={<CloudUploadIcon />}
            onClick={() => fileInputRef.current.click()}
            fullWidth
          >
            Select Files
          </Button>
          <TextField
            fullWidth
            variant="outlined"
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
            placeholder="Paste YouTube URL here"
            sx={{ mt: 2 }}
          />
          <Button
            variant="contained"
            color="secondary"
            onClick={handleUpload}
            disabled={isUploading || (files.length === 0 && !youtubeUrl)}
            sx={{ mt: 1 }}
            fullWidth
          >
            {isUploading ? <CircularProgress size={24} /> : 'Upload'}
          </Button>
          <Typography variant="subtitle1" sx={{ mt: 2 }}>
            Selected Files:
          </Typography>
          <FileList>
            {files.map((file, index) => (
              <FileListItem key={index}>
                <ListItemText primary={file.name} />
                <DeleteIcon onClick={() => handleRemoveFile(index)} />
              </FileListItem>
            ))}
          </FileList>
          <Typography variant="subtitle1" sx={{ mt: 2 }}>
            Uploaded Files:
          </Typography>
          <FileList>
            {uploadedFiles.map((file, index) => (
              <FileListItem key={index}>
                {file.type === 'youtube' ? (
                  <ListItemText
                    primary={file.name}
                    secondary={
                      <Link href={file.url} target="_blank" rel="noopener noreferrer">
                        YouTube Video
                      </Link>
                    }
                    icon={<YouTubeIcon />}
                  />
                ) : (
                  <ListItemText primary={file.name} icon={<PictureAsPdfIcon />} />
                )}
                <DeleteIcon onClick={() => handleRemoveUploadedFile(index)} />
              </FileListItem>
            ))}
          </FileList>
        </Sidebar>
        <MainContent>
          <Header variant="h2" component="h1">
            NeuralChat
          </Header>
          <ChatSection>
            <ConversationContainer>
              {conversation.map((item, index) => (
                item.type === 'user' ? (
                  <UserMessage key={index}>
                    <Typography>{item.text}</Typography>
                  </UserMessage>
                ) : (
                  <BotMessage key={index}>
                    <div dangerouslySetInnerHTML={renderMarkdown(item.text)} />
                  </BotMessage>
                )
              ))}
            </ConversationContainer>
            <InputSection>
              <TextField
                fullWidth
                variant="outlined"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question"
                onKeyPress={(e) => e.key === 'Enter' && handleAsk()}
              />
              <Button
                variant="contained"
                color="primary"
                onClick={handleAsk}
                disabled={isAsking}
                endIcon={isAsking ? <CircularProgress size={20} /> : <SendIcon />}
              >
                Ask
              </Button>
            </InputSection>
          </ChatSection>
        </MainContent>
      </AppContainer>
    </ThemeProvider>
  );
}

export default App;
