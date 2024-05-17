import { Amplify} from 'aws-amplify';
import { withAuthenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import './App.css';
import awsExports from './aws-exports.js';
import { fetchAuthSession } from 'aws-amplify/auth';
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ClipLoader } from 'react-spinners'; // Import the spinner component


Amplify.configure(awsExports);

async function currentSession() {
  try {
    const { accessToken, idToken } = (await fetchAuthSession()).tokens ?? {};
    return { accessToken, idToken };
  } catch (err) {
    console.log(err);
    return {};
  }
}

function App({ signOut, user, authData }) {
  const [idToken, setIdToken] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [parsedIdToken, setParsedIdToken] = useState('');
  const [parsedAccessToken, setParsedAccessToken] = useState('');
  const [inputPrompt, setinputPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false); // Add a state for loading
  const [sessionId, setSessionId] = useState(''); // Add a state for session ID


  useEffect(() => {
    async function fetchTokens() {
      try {
        const { accessToken, idToken } = await currentSession();
        setIdToken(idToken ? idToken.toString() : '');
        setAccessToken(accessToken ? accessToken.toString() : '');
        generateSessionId(); // Generate an initial session ID
        
      } catch (error) {
        console.error('Error fetching tokens:', error);
      }
    }

    fetchTokens();
  }, []);

const parseJwtToken = (tokenType) => {
  if (tokenType === 'idToken') {
    const parsedToken = parseJwt(idToken);
    setParsedIdToken(JSON.stringify(parsedToken, null, 2));
  } else if (tokenType === 'accessToken') {
    const parsedToken = parseJwt(accessToken);
    setParsedAccessToken(JSON.stringify(parsedToken, null, 2));
  }
};

  const handleInputChange = (e) => {
    setinputPrompt(e.target.value);
  };
  
  const generateSessionId = () => {
    const newSessionId = Math.random().toString(36).substring(2, 15); // Generate a new session ID
    setSessionId(newSessionId);
  };  
  
  return (
    <>
      <h1>Hello {user.username}</h1>
  
      <button onClick={signOut}>Sign out</button>
      <h2>ID Token:</h2>
      <pre className="token-textbox">{idToken.toString()}</pre>
      <button onClick={() => parseJwtToken('idToken')}>Parse ID Token</button>
      <pre>{parsedIdToken}</pre>
  
      <h2>Access Token:</h2>
      <pre className="token-textbox">{accessToken.toString()}</pre>
      <button onClick={() => parseJwtToken('accessToken')}>Parse Access Token</button>
      <pre>{parsedAccessToken}</pre>
  
      <input
        type="text"
        value={inputPrompt}
        onChange={handleInputChange}
        placeholder="Enter claim action"
      />
      <button onClick={() => callAPIGW(accessToken, idToken, inputPrompt, setIsLoading, sessionId)}>Call API Gateway</button>
  
      <button onClick={generateSessionId}>Reset Session</button>
      {isLoading && <ClipLoader color="#36d7b7" />} {/* Render the spinner when isLoading is true */}
      <div id="apiresponse"></div>
    </>
    
  );
}

/**
 * Call protected APIGW endpoint
 *
 * Important:
 *   Make sure apigw cognito authorizer configuration is complete
 *   Make sure api accepts id-token (no oauth scope defined in authorization)
 *   You can only use id-token since custom scopes are not supported when sdk is used
 */
function callAPIGW(accessToken, idToken, inputPrompt, setIsLoading, sessionId) {
  setIsLoading(true); // Set isLoading to true before making the API call

  const apiGatewayUrl = `${process.env.REACT_APP_API_GATEWAY_URL}/claims?inputPrompt=${encodeURIComponent(inputPrompt)}&sessionId=${sessionId}`;

  // set ID Token in "Authorization" header
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': idToken,
  };

  axios
    .get(apiGatewayUrl, { headers: headers })
    .then((response) => {
      console.log(response.data);
      document.getElementById('apiresponse').innerHTML =
        '<b>Response</b><br>' + JSON.stringify(response.data, null, 2);
      setIsLoading(false); // Set isLoading to false after receiving the response
        
    })
    .catch(function (error) {
      console.error(error);
      setIsLoading(false); // Set isLoading to false if an error occurs
      
    });
}

function parseJwt(token) {
  var base64Url = token.split('.')[1];
  var base64 = base64Url.replace('-', '+').replace('_', '/');
  return JSON.parse(window.atob(base64));
}

export default withAuthenticator(App);