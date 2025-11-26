import React from 'react';
import AdminPanel from './components/AdminPanel';
import ChatPanel from './components/ChatPanel';

export default function App(){
  const [view, setView] = React.useState('chat');
  const [selectedAgent, setSelectedAgent] = React.useState(null);

  return (
    <div style={{display:'flex', gap:20, padding:20}}>
      <div style={{width: '30%'}}>
        <button onClick={()=>setView('chat')}>Chat</button>
        <button onClick={()=>setView('admin')}>Admin</button>
        {view === 'admin' && <AdminPanel onSelectAgent={setSelectedAgent} />}
        {view === 'chat' && <ChatPanel selectedAgent={selectedAgent} onSelectAgent={setSelectedAgent} />}
      </div>
    </div>
  );
}
