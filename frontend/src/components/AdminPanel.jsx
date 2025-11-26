import React from 'react';
import axios from 'axios';

export default function AdminPanel({onSelectAgent}){
  const [agents, setAgents] = React.useState({});
  const [name, setName] = React.useState("");

  const load = async ()=> {
    const r = await axios.get('/api/agents');
    setAgents(r.data);
  };

  React.useEffect(()=>{ load(); }, []);

  const create = async () => {
    if(!name) return;
    await axios.post('/api/agents', {name});
    await load();
  };

  const start = async (a) => {
    await axios.post(`/api/agents/${a}/start`);
    await load();
  };

  const train = async (a) => {
    await axios.post(`/api/agents/${a}/train`);
  };

  return (
    <div>
      <h3>Agents</h3>
      <input value={name} onChange={e=>setName(e.target.value)} placeholder="agent name" />
      <button onClick={create}>Create</button>
      <ul>
        {Object.keys(agents).map(k=>(
          <li key={k}>
            <b>{k}</b> - port: {agents[k].port} - status: {agents[k].status}
            <button onClick={()=>onSelectAgent(k)}>Select</button>
            <button onClick={()=>train(k)}>Train</button>
            <button onClick={()=>start(k)}>Start</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
