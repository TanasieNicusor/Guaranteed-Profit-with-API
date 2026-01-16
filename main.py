import requests

class OddsApiClient:
    BASE_URL = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"

    def __init__(self, api_key):
        self.api_key = api_key

    def fetch_odds(self, regions="uk", markets="h2h", odds_format="decimal", date_format="iso"):
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
            "dateFormat": date_format
        }
        response = requests.get(self.BASE_URL, params=params)
        
        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code} {response.text}")
            
        return response

class Match:
    def __init__(self, match_data):
        self.home_team = match_data["home_team"]
        self.away_team = match_data["away_team"]
        self.commence_time = match_data["commence_time"]
        self.bookmakers = match_data["bookmakers"]

    def get_best_odds(self):
        """Finds the best odds offered across all bookmakers for each outcome."""
        best_odds = {}
        for bookmaker in self.bookmakers:
            bookmaker_name = bookmaker["title"]
            # We assume we are looking at the first market (e.g. h2h)
            try:
                market = bookmaker["markets"][0]
            except IndexError:
                continue

            for outcome in market["outcomes"]:
                name = outcome["name"]
                price = outcome["price"]

                # If this outcome is not recorded or we found a better price, update it
                if name not in best_odds or price > best_odds[name][0]:
                    best_odds[name] = (price, bookmaker_name)
        return best_odds

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"


class ArbitrageCalculator:
    def __init__(self, total_stake=100.0):
        self.total_stake = total_stake

    def evaluate(self, best_odds):
        """Calculates if an arbitrage opportunity exists."""
        if not best_odds:
            return None

        probabilities = [1 / price for price, _ in best_odds.values()]
        total_prob = sum(probabilities)
        
        result = {
            "total_prob": round(total_prob, 4),
            "is_arbitrage": total_prob < 1.0,
            "opportunities": [],
            "guaranteed_profit": 0.0
        }

        if result["is_arbitrage"]:
            # Calculate stakes for each outcome
            strokes = [(1 / price) / total_prob * self.total_stake for price, _ in best_odds.values()]
            
            # Record details for each bet
            for outcome_name, stake, (price, bookmaker) in zip(best_odds.keys(), strokes, best_odds.values()):
                result["opportunities"].append({
                    "outcome": outcome_name,
                    "stake": round(stake, 2),
                    "price": price,
                    "bookmaker": bookmaker
                })
            
            # Calculate guaranteed profit
            # Profit = (Stake * Price) - Total_Stake. Since it's arbitrage, this should be same roughly for all
            # We take the minimum to be safe
            min_return = min(stake * price for stake, (price, _) in zip(strokes, best_odds.values()))
            result["guaranteed_profit"] = round(min_return - self.total_stake, 2)
            
        return result


def main():
    API_KEY = "APY_KEY"
    
    try:
        client = OddsApiClient(API_KEY)
        response = client.fetch_odds()
        matches_data = response.json()
        
        # Display quota usage
        remaining = response.headers.get("x-requests-remaining", "N/A")
        used = response.headers.get("x-requests-used", "N/A")
        print(f"API credits used: {used}")
        print(f"API credits remaining: {remaining}\n")

        print("Premier League Odds:\n")

        calculator = ArbitrageCalculator(total_stake=100)

        for i, match_data in enumerate(matches_data, start=1):
            match = Match(match_data)
            print(f"\n{i}. {match}")
            print(f"   Start time: {match.commence_time}")

            best_odds = match.get_best_odds()
            arb_result = calculator.evaluate(best_odds)

            if arb_result:
                print("\n   Implied probability sum:", arb_result["total_prob"])

                if arb_result["is_arbitrage"]:
                    print("   Arbitrage opportunity detected!")
                    for opp in arb_result["opportunities"]:
                        print(f"     Bet {opp['stake']} on {opp['outcome']} at {opp['price']} ({opp['bookmaker']})")
                    print(f"   Guaranteed profit: {arb_result['guaranteed_profit']}")
                else:
                    print("   No arbitrage possible for this game.")
            
            print("-" * 50)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

