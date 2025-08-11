from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple
import uuid
from datetime import datetime
import random
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Chess Game Classes
class PieceType(str, Enum):
    BISHOP = "bishop"
    ROOK = "rook"

class PieceColor(str, Enum):
    WHITE = "white"
    BLACK = "black"

class Position(BaseModel):
    file: str  # a-h
    rank: int  # 1-8
    x: int     # 0-7 (internal)
    y: int     # 0-7 (internal)

class Piece:
    def __init__(self, piece_type: PieceType, color: PieceColor, position: Tuple[int, int]):
        self.piece_type = piece_type
        self.color = color
        self.x, self.y = position
    
    def get_position(self) -> Position:
        """Convert internal coordinates to chess notation"""
        file = chr(ord('a') + self.x)
        rank = self.y + 1
        return Position(file=file, rank=rank, x=self.x, y=self.y)
    
    def set_position(self, x: int, y: int):
        """Set piece position using internal coordinates"""
        self.x = x
        self.y = y

class Bishop(Piece):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(PieceType.BISHOP, PieceColor.WHITE, position)
    
    def can_capture(self, target_x: int, target_y: int) -> bool:
        """Check if bishop can capture a piece at target position"""
        # Bishop moves diagonally
        dx = abs(target_x - self.x)
        dy = abs(target_y - self.y)
        return dx == dy and dx > 0

class Rook(Piece):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(PieceType.ROOK, PieceColor.BLACK, position)
    
    def can_capture(self, target_x: int, target_y: int) -> bool:
        """Check if rook can capture a piece at target position"""
        # Rook moves horizontally or vertically
        return (self.x == target_x and self.y != target_y) or (self.y == target_y and self.x != target_x)

class Board:
    def __init__(self):
        self.size = 8
        # Initialize pieces: Bishop at c3 (2,2), Rook at h1 (7,0)
        self.bishop = Bishop((2, 2))  # c3
        self.rook = Rook((7, 0))      # h1
    
    def wrap_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """Handle board wrapping"""
        return x % self.size, y % self.size
    
    def move_rook(self, direction: str, squares: int) -> Tuple[int, int]:
        """Move rook and return new position with wrapping"""
        if direction == "up":
            new_x = self.rook.x
            new_y = self.rook.y + squares
        else:  # right
            new_x = self.rook.x + squares
            new_y = self.rook.y
        
        # Apply wrapping
        new_x, new_y = self.wrap_coordinates(new_x, new_y)
        self.rook.set_position(new_x, new_y)
        return new_x, new_y
    
    def check_capture(self) -> bool:
        """Check if rook is captured by bishop"""
        return self.bishop.can_capture(self.rook.x, self.rook.y)
    
    def get_board_state(self) -> dict:
        """Get current board state"""
        return {
            "bishop_position": self.bishop.get_position().dict(),
            "rook_position": self.rook.get_position().dict(),
            "captured": self.check_capture()
        }

# Game Models
class CoinToss(BaseModel):
    result: str  # "heads" or "tails"
    direction: str  # "up" or "right"

class DiceRoll(BaseModel):
    die1: int
    die2: int
    total: int

class GameRound(BaseModel):
    round_number: int
    coin_toss: CoinToss
    dice_roll: DiceRoll
    rook_position_before: Position
    rook_position_after: Position
    captured: bool

class GameState(BaseModel):
    game_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rounds: List[GameRound] = []
    current_round: int = 0
    game_over: bool = False
    winner: Optional[str] = None
    bishop_position: Position
    rook_position: Position
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GameCreate(BaseModel):
    pass

class GameService:
    def __init__(self):
        self.games = {}
    
    def create_game(self) -> GameState:
        """Create a new game"""
        board = Board()
        game_state = GameState(
            bishop_position=board.bishop.get_position(),
            rook_position=board.rook.get_position()
        )
        self.games[game_state.game_id] = {
            "state": game_state,
            "board": board
        }
        return game_state
    
    def get_game(self, game_id: str) -> Optional[GameState]:
        """Get game state"""
        if game_id in self.games:
            return self.games[game_id]["state"]
        return None
    
    def play_round(self, game_id: str) -> Optional[GameState]:
        """Play one round of the game"""
        if game_id not in self.games:
            return None
        
        game_data = self.games[game_id]
        game_state = game_data["state"]
        board = game_data["board"]
        
        if game_state.game_over:
            return game_state
        
        # Increment round
        game_state.current_round += 1
        
        # Record position before move
        position_before = board.rook.get_position()
        
        # Coin toss
        coin_result = random.choice(["heads", "tails"])
        direction = "up" if coin_result == "heads" else "right"
        coin_toss = CoinToss(result=coin_result, direction=direction)
        
        # Dice roll
        die1 = random.randint(1, 6)
        die2 = random.randint(1, 6)
        total = die1 + die2
        dice_roll = DiceRoll(die1=die1, die2=die2, total=total)
        
        # Move rook
        board.move_rook(direction, total)
        position_after = board.rook.get_position()
        
        # Check capture
        captured = board.check_capture()
        
        # Create round record
        game_round = GameRound(
            round_number=game_state.current_round,
            coin_toss=coin_toss,
            dice_roll=dice_roll,
            rook_position_before=position_before,
            rook_position_after=position_after,
            captured=captured
        )
        
        game_state.rounds.append(game_round)
        game_state.rook_position = position_after
        
        # Check game over conditions
        if captured:
            game_state.game_over = True
            game_state.winner = "Bishop (White)"
        elif game_state.current_round >= 15:
            game_state.game_over = True
            game_state.winner = "Rook (Black)"
        
        return game_state

# Initialize game service
game_service = GameService()

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Chess Game API"}

@api_router.post("/game", response_model=GameState)
async def create_game():
    """Create a new chess game"""
    return game_service.create_game()

@api_router.get("/game/{game_id}", response_model=GameState)
async def get_game(game_id: str):
    """Get game state"""
    game_state = game_service.get_game(game_id)
    if not game_state:
        raise HTTPException(status_code=404, detail="Game not found")
    return game_state

@api_router.post("/game/{game_id}/round", response_model=GameState)
async def play_round(game_id: str):
    """Play one round of the game"""
    game_state = game_service.play_round(game_id)
    if not game_state:
        raise HTTPException(status_code=404, detail="Game not found")
    return game_state

@api_router.post("/game/{game_id}/reset", response_model=GameState)
async def reset_game(game_id: str):
    """Reset game to initial state"""
    if game_id not in game_service.games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Create new board and reset game state
    board = Board()
    game_state = GameState(
        game_id=game_id,
        bishop_position=board.bishop.get_position(),
        rook_position=board.rook.get_position()
    )
    
    game_service.games[game_id] = {
        "state": game_state,
        "board": board
    }
    
    return game_state

# Original status check endpoints (keeping for compatibility)
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()