import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { RefreshCw, ExternalLink, Clock3, AlertTriangle, BookOpen, TrendingUp, Brain } from "lucide-react";
import "./style.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
function timeAgo(value) {
  if (!value) return "time unavailable";
  const d = new Date(value);
  if (isNaN(d)) return value;
  return d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}
const categoryIcon = (cat) => {
  if (cat?.includes("TRADE")) return <TrendingUp size={16}/>;
  if (cat?.includes("MINDSET")) return <Brain size={16}/>;
  if (cat?.includes("LEARNING")) return <BookOpen size={16}/>;
  return <AlertTriangle size={16}/>;
}
function App() {
  const [brief, setBrief] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function load() {
    setLoading(true); setError("");
    try {
      const [b,p] = await Promise.all([
        fetch(`${API}/api/brief`).then(r => { if(!r.ok) throw Error("API unavailable"); return r.json(); }),
        fetch(`${API}/api/posts?limit=40`).then(r => r.json())
      ]);
      setBrief(b); setPosts(p);
    } catch(e) { setError("Could not connect to Market Brief backend. Check the API URL and make sure the server is running."); }
    finally { setLoading(false); }
  }
  async function refresh() {
    setLoading(true); setError("");
    try { await fetch(`${API}/api/refresh`, {method:"POST"}).then(r => { if(!r.ok) throw Error(); return r.json(); }); await load(); }
    catch(e) { setError("Refresh failed. The Telegram public preview may be temporarily unavailable."); setLoading(false); }
  }
  useEffect(() => { load(); const timer=setInterval(load, 60000); return () => clearInterval(timer); }, []);
  const important = posts.filter(p => p.priority === "critical" || p.priority === "high");
  return <main className="app">
    <header className="top">
      <div className="brand"><div className="logo">MB</div><div><h1>Market Brief</h1><p>Trading With Sidhant · Public feed</p></div></div>
      <button className="refresh" onClick={refresh} disabled={loading}><RefreshCw size={17} className={loading?"spin":""}/>{loading?"Updating":"Refresh"}</button>
    </header>
    <section className="hero">
      <div className="eyebrow">YOUR MARKET IN 2 MINUTES</div>
      <h2>Catch up.<br/><span>Don't scroll.</span></h2>
      <p className="muted">Posts sorted by signal, not noise.</p>
      <div className="stats"><div><strong>{posts.length}</strong><small>saved posts</small></div><div><strong>{important.length}</strong><small>high priority</small></div><div><strong>{brief?.updated_at?timeAgo(brief.updated_at):"—"}</strong><small>last updated</small></div></div>
    </section>
    {error && <div className="error">{error}</div>}
    <section className="section">
      <div className="sectionTitle"><h3>Brief</h3><span className="tag">BASIC V1</span></div>
      <div className="briefCard">
        {(brief?.summary || "Fetching posts…").split("\n\n").map((line,i)=><p key={i}>{line}</p>)}
        <small>Automated grouping, not personalized financial advice. Verify original posts before acting.</small>
      </div>
    </section>
    <section className="section">
      <div className="sectionTitle"><h3>Recent channel posts</h3><span className="muted">{posts.length} stored</span></div>
      {posts.length===0 && <div className="empty">No posts fetched yet.</div>}
      <div className="feed">{posts.map(p=><article className="post" key={p.id}>
        <div className="postMeta"><span className={`category ${p.priority}`}>{categoryIcon(p.category)}{p.category}</span><time>{timeAgo(p.posted_at)}</time></div>
        <p className="postText">{p.text}</p>
        <a href={p.url} target="_blank" rel="noreferrer">Open original post <ExternalLink size={14}/></a>
      </article>)}</div>
    </section>
    <footer>Market Brief · V1 · Informational tool only</footer>
  </main>
}
createRoot(document.getElementById("root")).render(<App/>);
