import React from 'react';

const Sidebar = ({ onNewChat, selectedRegion, onRegionChange }) => {
  const regions = ["All", "India", "SE Asia", "North America", "South America", "Middle East", "Australia", "Africa", "Europe"];

  return (
    <aside className="sidebar">
      <button className="new-chat-btn" onClick={onNewChat}>
        + New Chat
      </button>

      <div className="region-selector" style={{ marginTop: '20px', padding: '0 10px' }}>
        <label style={{ color: '#fff', fontSize: '0.9em', marginBottom: '5px', display: 'block' }}>Region</label>
        <select 
          value={selectedRegion} 
          onChange={(e) => onRegionChange(e.target.value)}
          style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #444', backgroundColor: '#333', color: 'white' }}
        >
          {regions.map(region => (
            <option key={region} value={region}>{region}</option>
          ))}
        </select>
      </div>
      
      <div className="history-list" style={{ marginTop: '20px', fontSize: '0.9rem' }}>
        <p style={{ padding: '10px', color: 'var(--text-secondary)' }}>Today</p>
        <button className="new-chat-btn" style={{ border: 'none', width: '100%', marginBottom: '5px' }}>
          Mock Chat History 1
        </button>
        <button className="new-chat-btn" style={{ border: 'none', width: '100%', marginBottom: '5px' }}>
          Previous conversation...
        </button>
      </div>
      
      <div style={{ marginTop: 'auto', borderTop: '1px solid var(--border-color)', padding: '10px 0' }}>
         {/* User profile placeholder */}
         <div className="new-chat-btn" style={{ border: 'none' }}>
            <div className="avatar user" style={{ width: '20px', height: '20px', marginRight: '10px' }}>U</div>
            User
         </div>
      </div>
    </aside>
  );
};

export default Sidebar;
