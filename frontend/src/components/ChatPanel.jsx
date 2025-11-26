import React from 'react';
import axios from 'axios';

export default function ChatPanel({selectedAgent, onSelectAgent}){
  const [agents, setAgents] = React.useState({});
  const [agent, setAgent] = React.useState(selectedAgent);
  const [message, setMessage] = React.useState("");
  const [trace, setTrace] = React.useState(null);
  const [conversationId, setConversationId] = React.useState("default");

  React.useEffect(()=>{
    axios.get('/api/agents').then(r=>{
      setAgents(r.data);
      if(selectedAgent) setAgent(selectedAgent);
    });
  }, [selectedAgent]);

  const send = async () => {
    if(!agent) { alert("Select agent"); return; }
    const r = await axios.post(`/api/agents/${agent}/chat`, {text: message, conversation_id: conversationId});
    setTrace(r.data);
    // if transferred, show transfer info
  };

  return (
    <div>
      <h3>Chat</h3>
      <div>
        <label>Agent:</label>
        <select value={agent || ""} onChange={e=>setAgent(e.target.value)}>
          <option value="">--select--</option>
          {Object.keys(agents).map(k=> <option key={k} value={k}>{k}</option>)}
        </select>
        <button onClick={()=>onSelectAgent(agent)}>Use</button>
      </div>

      <div style={{marginTop:10}}>
        <input value={message} onChange={e=>setMessage(e.target.value)} placeholder="message" />
        <button onClick={send}>Send</button>
      </div>

      <h4>Trace</h4>
      <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(trace, null, 2)}</pre>

      <h4>Embedded Webchat (optional)</h4>
      <p>Ниже показан встроенный webchat — для него React динамически подключает Rasa Webchat script и настраивает socketUrl на порт выбранного агента.</p>
      <div id="rasa-webchat" />
      <WebchatEmbed key={agent} agent={agent} agents={agents} />
    </div>
  );
}

// Helper component to load Webchat dynamically and init it
function WebchatEmbed({agent, agents}){
  React.useEffect(()=>{
    if(!agent) return;
    const scriptId = 'rasa-webchat-script';
    const existing = document.getElementById(scriptId);
    if(!existing){
      const s = document.createElement('script');
      s.id = scriptId;
      s.src = "https://unpkg.com/@rasahq/rasa-webchat@1.0.1/lib/index.js";
      s.async = true;
      document.body.appendChild(s);
      s.onload = () => initWebchat();
    } else {
      initWebchat();
    }
    function initWebchat(){
      const port = agents[agent]?.port || 5005;
      // remove existing chat div
      const el = document.getElementById('rasa-webchat');
      el.innerHTML = '';
      // Create widget
      // WebChat is a global from the script
      if(window.WebChat){
        window.WebChat.default({
          selector: "#rasa-webchat",
          initPayload: "/get_started",
          customData: {"agent": agent},
          socketUrl: `http://localhost:${port}`,
          socketPath: "/socket.io/",
          title: `Agent: ${agent}`,
          subtitle: "Rasa Webchat"
        });
      }
    }
    // cleanup on unmount
    return ()=> {
      const el = document.getElementById('rasa-webchat');
      if(el) el.innerHTML = '';
    };
  }, [agent, agents]);

  return null;
}