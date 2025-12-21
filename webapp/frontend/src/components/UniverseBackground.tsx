import React from 'react';

const UniverseBackground: React.FC = () => {
  return (
    <div className="universe-bg">
      {/* Stars layer */}
      <div className="stars-layer" />
      <div className="stars-layer-2" />
      
      {/* Milky Way band */}
      <div className="milky-way" />
      
      {/* Nebula clouds */}
      <div className="nebula nebula-1" />
      <div className="nebula nebula-2" />
      <div className="nebula nebula-3" />
      
      {/* Planets */}
      <div className="planet planet-1">
        <div className="planet-ring" />
      </div>
      <div className="planet planet-2" />
      <div className="planet planet-3" />
      <div className="planet planet-4" />
      <div className="planet planet-5" />
    </div>
  );
};

export default UniverseBackground;
