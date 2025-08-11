import requests
import sys
from datetime import datetime
import json

class ChessGameAPITester:
    def __init__(self, base_url="https://062cb6a2-b5cb-4e06-848e-b435468f0e69.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.current_game_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else self.api_url
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)

            print(f"   Response Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_api_root(self):
        """Test API root endpoint"""
        success, response = self.run_test(
            "API Root",
            "GET",
            "",
            200
        )
        return success

    def test_create_game(self):
        """Test creating a new game"""
        success, response = self.run_test(
            "Create New Game",
            "POST",
            "game",
            200
        )
        
        if success and 'game_id' in response:
            self.current_game_id = response['game_id']
            print(f"   Game ID: {self.current_game_id}")
            
            # Verify initial positions
            bishop_pos = response.get('bishop_position', {})
            rook_pos = response.get('rook_position', {})
            
            if bishop_pos.get('file') == 'c' and bishop_pos.get('rank') == 3:
                print("✅ Bishop correctly positioned at c3")
            else:
                print(f"❌ Bishop position incorrect: {bishop_pos}")
                
            if rook_pos.get('file') == 'h' and rook_pos.get('rank') == 1:
                print("✅ Rook correctly positioned at h1")
            else:
                print(f"❌ Rook position incorrect: {rook_pos}")
                
            return True
        return False

    def test_get_game(self):
        """Test getting game state"""
        if not self.current_game_id:
            print("❌ No game ID available for testing")
            return False
            
        success, response = self.run_test(
            "Get Game State",
            "GET",
            f"game/{self.current_game_id}",
            200
        )
        return success

    def test_play_round(self):
        """Test playing a round"""
        if not self.current_game_id:
            print("❌ No game ID available for testing")
            return False
            
        success, response = self.run_test(
            "Play Round",
            "POST",
            f"game/{self.current_game_id}/round",
            200
        )
        
        if success:
            # Verify round data structure
            rounds = response.get('rounds', [])
            if len(rounds) > 0:
                last_round = rounds[-1]
                print(f"   Round {last_round.get('round_number')} played")
                print(f"   Coin toss: {last_round.get('coin_toss', {}).get('result')} -> {last_round.get('coin_toss', {}).get('direction')}")
                print(f"   Dice roll: {last_round.get('dice_roll', {}).get('die1')} + {last_round.get('dice_roll', {}).get('die2')} = {last_round.get('dice_roll', {}).get('total')}")
                print(f"   Rook moved: {last_round.get('rook_position_before', {}).get('file')}{last_round.get('rook_position_before', {}).get('rank')} -> {last_round.get('rook_position_after', {}).get('file')}{last_round.get('rook_position_after', {}).get('rank')}")
                print(f"   Captured: {last_round.get('captured', False)}")
                
        return success

    def test_multiple_rounds(self):
        """Test playing multiple rounds to check game mechanics"""
        if not self.current_game_id:
            print("❌ No game ID available for testing")
            return False
            
        print(f"\n🎮 Testing multiple rounds for game mechanics...")
        rounds_to_play = 5
        successful_rounds = 0
        
        for i in range(rounds_to_play):
            success, response = self.run_test(
                f"Play Round {i+1}",
                "POST",
                f"game/{self.current_game_id}/round",
                200
            )
            
            if success:
                successful_rounds += 1
                current_round = response.get('current_round', 0)
                game_over = response.get('game_over', False)
                
                if game_over:
                    winner = response.get('winner', 'Unknown')
                    print(f"🎉 Game ended after {current_round} rounds! Winner: {winner}")
                    break
            else:
                break
                
        print(f"   Successfully played {successful_rounds} rounds")
        return successful_rounds > 0

    def test_reset_game(self):
        """Test resetting a game"""
        if not self.current_game_id:
            print("❌ No game ID available for testing")
            return False
            
        success, response = self.run_test(
            "Reset Game",
            "POST",
            f"game/{self.current_game_id}/reset",
            200
        )
        
        if success:
            # Verify reset worked
            current_round = response.get('current_round', -1)
            rounds = response.get('rounds', [])
            game_over = response.get('game_over', True)
            
            if current_round == 0 and len(rounds) == 0 and not game_over:
                print("✅ Game successfully reset to initial state")
            else:
                print(f"❌ Reset may not have worked properly - Round: {current_round}, Rounds: {len(rounds)}, Game Over: {game_over}")
                
        return success

    def test_invalid_game_id(self):
        """Test with invalid game ID"""
        success, response = self.run_test(
            "Invalid Game ID",
            "GET",
            "game/invalid-id-123",
            404
        )
        return success

def main():
    print("🚀 Starting Chess Game API Tests")
    print("=" * 50)
    
    # Setup
    tester = ChessGameAPITester()
    
    # Run tests in sequence
    tests = [
        ("API Root", tester.test_api_root),
        ("Create Game", tester.test_create_game),
        ("Get Game State", tester.test_get_game),
        ("Play Single Round", tester.test_play_round),
        ("Play Multiple Rounds", tester.test_multiple_rounds),
        ("Reset Game", tester.test_reset_game),
        ("Invalid Game ID", tester.test_invalid_game_id),
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! Backend API is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())