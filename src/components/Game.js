import React, { useState, useEffect } from 'react';

const Game = () => {
  const [currentImage, setCurrentImage] = useState(null);
  const [userGuess, setUserGuess] = useState('');
  const [score, setScore] = useState(0);
  const [feedback, setFeedback] = useState('');
  const [showAnswer, setShowAnswer] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchRandomImage();
    // eslint-disable-next-line
  }, []);

  const fetchRandomImage = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('http://r630:5000/api/random-image');
      if (!response.ok) {
        throw new Error('Failed to fetch image');
      }
      const data = await response.json();
      setCurrentImage(data);
      setShowAnswer(false);
      setFeedback('');
      setUserGuess('');
    } catch (error) {
      setError('Failed to load image. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGuess = (e) => {
    e.preventDefault();
    if (!userGuess) return;
    // For now, just show the answer and feedback
    setFeedback('Thanks for your guess!');
    setShowAnswer(true);
  };

  return (
    <div className="game-container">
      <h1>Clock Picture</h1>
      <div className="score">Score: {score}</div>
      {loading && <div>Loading...</div>}
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {currentImage && !loading && (
        <div className="image-container">
          <a href={currentImage.source} target="_blank" rel="noopener noreferrer">
            <img src={currentImage.url} alt="Guess the year" style={{ maxWidth: '100%', maxHeight: 400 }} />
          </a>
        </div>
      )}
      {!showAnswer && !loading && currentImage && (
        <form onSubmit={handleGuess}>
          <input
            type="number"
            value={userGuess}
            onChange={(e) => setUserGuess(e.target.value)}
            placeholder="Enter year"
            min="0"
            max="9999"
          />
          <button type="submit">Submit Guess</button>
        </form>
      )}
      {showAnswer && currentImage && (
        <div className="feedback">
          <p>{feedback}</p>
          {/* You can add more feedback logic here, e.g., how close the guess was */}
          <p><strong>Article:</strong> {currentImage.title}</p>
          <a href={currentImage.source} target="_blank" rel="noopener noreferrer">
            View on Wikipedia
          </a>
          <button onClick={fetchRandomImage}>Next Image</button>
        </div>
      )}
    </div>
  );
};

export default Game; 