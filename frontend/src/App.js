import { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ChessBoard = ({ gameState }) => {
  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  const ranks = [8, 7, 6, 5, 4, 3, 2, 1]; // Display from top to bottom

  const getPieceAt = (file, rank) => {
    if (gameState.bishop_position.file === file && gameState.bishop_position.rank === rank) {
      return '♗'; // White bishop
    }
    if (gameState.rook_position.file === file && gameState.rook_position.rank === rank) {
      return '♜'; // Black rook
    }
    return '';
  };

  const isHighlighted = (file, rank) => {
    // Highlight if rook is captured
    if (gameState.rook_position.file === file && gameState.rook_position.rank === rank) {
      return gameState.rounds.length > 0 && gameState.rounds[gameState.rounds.length - 1]?.captured;
    }
    return false;
  };

  return (
    <div className="chess-board">
      <div className="board-header">
        <div className="file-labels">
          <div className="rank-label"></div>
          {files.map(file => (
            <div key={file} className="file-label">{file}</div>
          ))}
        </div>
      </div>
      <div className="board-grid">
        {ranks.map(rank => (
          <div key={rank} className="board-row">
            <div className="rank-label">{rank}</div>
            {files.map(file => {
              const isLight = (files.indexOf(file) + ranks.indexOf(rank)) % 2 === 0;
              const piece = getPieceAt(file, rank);
              const highlighted = isHighlighted(file, rank);
              
              return (
                <div
                  key={`${file}${rank}`}
                  className={`square ${isLight ? 'light' : 'dark'} ${highlighted ? 'captured' : ''}`}
                >
                  <span className="piece">{piece}</span>
                  <span className="coordinate">{file}{rank}</span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};

const GameControls = ({ gameState, onNewGame, onPlayRound, onResetGame }) => {
  return (
    <div className="game-controls">
      <div className="control-buttons">
        <button 
          onClick={onNewGame}
          className="btn btn-primary"
        >
          New Game
        </button>
        <button 
          onClick={onPlayRound}
          disabled={gameState?.game_over}
          className="btn btn-secondary"
        >
          Next Round
        </button>
        <button 
          onClick={onResetGame}
          disabled={!gameState}
          className="btn btn-tertiary"
        >
          Reset Current Game
        </button>
      </div>
      
      {gameState && (
        <div className="game-info">
          <div className="round-info">
            Round: {gameState.current_round} / 15
          </div>
          {gameState.game_over && (
            <div className="game-result">
              🎉 Game Over! Winner: {gameState.winner}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const RoundHistory = ({ rounds }) => {
  if (!rounds || rounds.length === 0) {
    return <div className="round-history">No rounds played yet.</div>;
  }

  return (
    <div className="round-history">
      <h3>Round History</h3>
      <div className="rounds-list">
        {rounds.map((round, index) => (
          <div key={index} className={`round-item ${round.captured ? 'captured-round' : ''}`}>
            <div className="round-header">
              <strong>Round {round.round_number}</strong>
              {round.captured && <span className="captured-badge">⚠️ CAPTURED!</span>}
            </div>
            
            <div className="round-details">
              <div className="coin-dice">
                <span className="coin">
                  🪙 {round.coin_toss.result} → {round.coin_toss.direction}
                </span>
                <span className="dice">
                  🎲 {round.dice_roll.die1} + {round.dice_roll.die2} = {round.dice_roll.total}
                </span>
              </div>
              
              <div className="movement">
                <span>
                  ♜ {round.rook_position_before.file}{round.rook_position_before.rank} → 
                  {round.rook_position_after.file}{round.rook_position_after.rank}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

function App() {
  const [gameState, setGameState] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleError = (error, action) => {
    console.error(`Error ${action}:`, error);
    setError(`Failed to ${action}. Please try again.`);
    setLoading(false);
  };

  const createNewGame = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${API}/game`);
      setGameState(response.data);
    } catch (error) {
      handleError(error, 'create new game');
    } finally {
      setLoading(false);
    }
  };

  const playRound = async () => {
    if (!gameState || gameState.game_over) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${API}/game/${gameState.game_id}/round`);
      setGameState(response.data);
    } catch (error) {
      handleError(error, 'play round');
    } finally {
      setLoading(false);
    }
  };

  const resetGame = async () => {
    if (!gameState) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${API}/game/${gameState.game_id}/reset`);
      setGameState(response.data);
    } catch (error) {
      handleError(error, 'reset game');
    } finally {
      setLoading(false);
    }
  };

  // Test API connection on load
  useEffect(() => {
    const testAPI = async () => {
      try {
        await axios.get(`${API}/`);
        console.log("API connection successful");
      } catch (error) {
        console.error("API connection failed:", error);
        setError("Unable to connect to game server");
      }
    };
    testAPI();
  }, []);

  return (
    <div className="App">
      <header className="app-header">
        <h1>Special Chess Game</h1>
        <p>Bishop vs Rook - Can the rook survive 15 rounds?</p>
      </header>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <main className="game-container">
        <div className="game-section">
          <GameControls
            gameState={gameState}
            onNewGame={createNewGame}
            onPlayRound={playRound}
            onResetGame={resetGame}
          />
          
          {loading && <div className="loading">Processing...</div>}
          
          {gameState && (
            <div className="game-board-container">
              <ChessBoard gameState={gameState} />
              
              <div className="game-legend">
                <div className="legend-item">
                  <span className="piece">♗</span> White Bishop (c3) - Stationary
                </div>
                <div className="legend-item">
                  <span className="piece">♜</span> Black Rook - Moves by coin toss & dice
                </div>
                <div className="legend-note">
                  Coin: Heads = Up, Tails = Right | Board wraps around edges
                </div>
              </div>
            </div>
          )}
        </div>
        
        {gameState && gameState.rounds && (
          <div className="history-section">
            <RoundHistory rounds={gameState.rounds} />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;