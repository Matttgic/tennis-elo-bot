import pandas as pd
import requests
import json
from datetime import datetime, date
import time
from typing import Dict, List, Tuple, Optional
import logging

# Configuration depuis les variables d'environnement (GitHub Actions)
import os

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'VOTRE_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', 'VOTRE_CHAT_ID')
ODDS_API_KEY = os.getenv('ODDS_API_KEY', 'VOTRE_ODDS_API_KEY')
TENNIS_API_KEY = os.getenv('TENNIS_API_KEY', 'VOTRE_TENNIS_API_KEY')

# Chemins vers les fichiers CSV
ATP_ELO_FILE = "atp_elo.csv"
WTA_ELO_FILE = "wta_elo.csv"

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TennisEloBot:
    def __init__(self):
        self.atp_elo = {}
        self.wta_elo = {}
        self.load_elo_data()
    
    def load_elo_data(self):
        """Charge les données ELO depuis les fichiers CSV"""
        try:
            # Chargement ATP ELO
            atp_df = pd.read_csv(ATP_ELO_FILE)
            for _, row in atp_df.iterrows():
                player_name = row['player_name'].lower().strip()
                self.atp_elo[player_name] = {
                    'hard': row.get('elo_hard', 1500),
                    'clay': row.get('elo_clay', 1500),
                    'grass': row.get('elo_grass', 1500),
                    'overall': row.get('elo_overall', 1500)
                }
            
            # Chargement WTA ELO
            wta_df = pd.read_csv(WTA_ELO_FILE)
            for _, row in wta_df.iterrows():
                player_name = row['player_name'].lower().strip()
                self.wta_elo[player_name] = {
                    'hard': row.get('elo_hard', 1500),
                    'clay': row.get('elo_clay', 1500),
                    'grass': row.get('elo_grass', 1500),
                    'overall': row.get('elo_overall', 1500)
                }
            
            logger.info(f"Chargé {len(self.atp_elo)} joueurs ATP et {len(self.wta_elo)} joueuses WTA")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données ELO: {e}")
    
    def normalize_player_name(self, name: str) -> str:
        """Normalise le nom du joueur pour la recherche"""
        return name.lower().strip().replace(".", "").replace("-", " ")
    
    def find_player_elo(self, player_name: str, tour: str) -> Dict:
        """Trouve l'ELO d'un joueur"""
        normalized_name = self.normalize_player_name(player_name)
        
        # Recherche directe
        elo_data = self.atp_elo if tour.upper() == 'ATP' else self.wta_elo
        if normalized_name in elo_data:
            return elo_data[normalized_name]
        
        # Recherche approximative (nom contenu dans la clé)
        for stored_name, elo in elo_data.items():
            if normalized_name in stored_name or stored_name in normalized_name:
                return elo
        
        # Recherche par mots
        name_parts = normalized_name.split()
        if len(name_parts) >= 2:
            for stored_name, elo in elo_data.items():
                if all(part in stored_name for part in name_parts):
                    return elo
        
        # ELO par défaut si joueur non trouvé
        return {'hard': 1500, 'clay': 1500, 'grass': 1500, 'overall': 1500}
    
    def get_surface_from_tournament(self, tournament_name: str) -> str:
        """Détermine la surface selon le nom du tournoi"""
        tournament_lower = tournament_name.lower()
        
        if any(keyword in tournament_lower for keyword in ['roland', 'garros', 'french', 'rome', 'madrid', 'monte carlo', 'barcelona']):
            return 'clay'
        elif any(keyword in tournament_lower for keyword in ['wimbledon', 'queens', 'halle', 'eastbourne']):
            return 'grass'
        else:
            return 'hard'  # Surface par défaut
    
    def get_matches_from_odds_api(self) -> List[Dict]:
        """Récupère les matchs depuis l'API Odds"""
        matches = []
        
        try:
            # ATP matches
            atp_url = f"https://api.the-odds-api.com/v4/sports/tennis_atp/odds/?apiKey={ODDS_API_KEY}&regions=us&markets=h2h"
            atp_response = requests.get(atp_url, timeout=10)
            
            if atp_response.status_code == 200:
                atp_data = atp_response.json()
                for match in atp_data:
                    if self.is_today(match['commence_time']):
                        matches.append({
                            'player1': match['home_team'],
                            'player2': match['away_team'],
                            'tour': 'ATP',
                            'tournament': match.get('sport_title', 'Unknown'),
                            'commence_time': match['commence_time']
                        })
            
            # WTA matches
            wta_url = f"https://api.the-odds-api.com/v4/sports/tennis_wta/odds/?apiKey={ODDS_API_KEY}&regions=us&markets=h2h"
            wta_response = requests.get(wta_url, timeout=10)
            
            if wta_response.status_code == 200:
                wta_data = wta_response.json()
                for match in wta_data:
                    if self.is_today(match['commence_time']):
                        matches.append({
                            'player1': match['home_team'],
                            'player2': match['away_team'],
                            'tour': 'WTA',
                            'tournament': match.get('sport_title', 'Unknown'),
                            'commence_time': match['commence_time']
                        })
            
        except Exception as e:
            logger.error(f"Erreur API Odds: {e}")
        
        return matches
    
    def get_matches_from_tennis_api(self) -> List[Dict]:
        """Récupère les matchs depuis Tennis API"""
        matches = []
        
        try:
            today_str = date.today().strftime('%Y-%m-%d')
            url = f"https://api.api-tennis.com/tennis/?met=Matchs&APIkey={TENNIS_API_KEY}&date={today_str}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    for match in data['result']:
                        matches.append({
                            'player1': match.get('match_hometeam_name', ''),
                            'player2': match.get('match_awayteam_name', ''),
                            'tour': 'ATP' if match.get('league_name', '').upper().find('ATP') != -1 else 'WTA',
                            'tournament': match.get('league_name', 'Unknown'),
                            'commence_time': match.get('match_date', '')
                        })
            
        except Exception as e:
            logger.error(f"Erreur Tennis API: {e}")
        
        return matches
    
    def is_today(self, date_string: str) -> bool:
        """Vérifie si la date correspond à aujourd'hui"""
        try:
            match_date = datetime.fromisoformat(date_string.replace('Z', '+00:00')).date()
            return match_date == date.today()
        except:
            return False
    
    def calculate_elo_differences(self, matches: List[Dict]) -> List[Dict]:
        """Calcule les différences d'ELO pour chaque match"""
        match_analyses = []
        
        for match in matches:
            try:
                surface = self.get_surface_from_tournament(match['tournament'])
                
                player1_elo_data = self.find_player_elo(match['player1'], match['tour'])
                player2_elo_data = self.find_player_elo(match['player2'], match['tour'])
                
                player1_elo = player1_elo_data[surface]
                player2_elo = player2_elo_data[surface]
                
                elo_diff = abs(player1_elo - player2_elo)
                
                match_analyses.append({
                    'player1': match['player1'],
                    'player1_elo': player1_elo,
                    'player2': match['player2'],
                    'player2_elo': player2_elo,
                    'surface': surface,
                    'elo_difference': elo_diff,
                    'tour': match['tour'],
                    'tournament': match['tournament'],
                    'commence_time': match['commence_time']
                })
                
            except Exception as e:
                logger.error(f"Erreur calcul ELO pour {match}: {e}")
        
        # Tri par différence d'ELO décroissante
        return sorted(match_analyses, key=lambda x: x['elo_difference'], reverse=True)
    
    def format_telegram_message(self, matches: List[Dict]) -> str:
        """Formate le message pour Telegram"""
        if not matches:
            return "🎾 Aucun match trouvé pour aujourd'hui"
        
        message = f"🎾 **MATCHS TENNIS DU {date.today().strftime('%d/%m/%Y')}**\n"
        message += f"📊 Classés par écart d'ELO (du plus grand au plus petit)\n\n"
        
        for i, match in enumerate(matches, 1):
            higher_elo_player = match['player1'] if match['player1_elo'] > match['player2_elo'] else match['player2']
            lower_elo_player = match['player2'] if match['player1_elo'] > match['player2_elo'] else match['player1']
            higher_elo = max(match['player1_elo'], match['player2_elo'])
            lower_elo = min(match['player1_elo'], match['player2_elo'])
            
            # Icône selon l'écart
            if match['elo_difference'] > 200:
                icon = "🔥"
            elif match['elo_difference'] > 100:
                icon = "⚡"
            else:
                icon = "⚖️"
            
            message += f"{icon} **Match {i}** ({match['tour']})\n"
            message += f"🏆 {higher_elo_player} ({higher_elo})\n"
            message += f"🆚 {lower_elo_player} ({lower_elo})\n"
            message += f"🎯 Surface: {match['surface'].title()}\n"
            message += f"📈 Écart ELO: **{match['elo_difference']}**\n"
            message += f"🏟️ {match['tournament']}\n\n"
        
        return message
    
    def send_telegram_message(self, message: str):
        """Envoie le message sur Telegram"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            
            # Diviser le message si trop long
            max_length = 4096
            if len(message) > max_length:
                parts = [message[i:i+max_length] for i in range(0, len(message), max_length)]
                for part in parts:
                    payload = {
                        'chat_id': TELEGRAM_CHAT_ID,
                        'text': part,
                        'parse_mode': 'Markdown'
                    }
                    requests.post(url, json=payload)
                    time.sleep(1)  # Éviter le rate limiting
            else:
                payload = {
                    'chat_id': TELEGRAM_CHAT_ID,
                    'text': message,
                    'parse_mode': 'Markdown'
                }
                
                response = requests.post(url, json=payload)
                if response.status_code == 200:
                    logger.info("Message envoyé avec succès sur Telegram")
                else:
                    logger.error(f"Erreur envoi Telegram: {response.text}")
                    
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message: {e}")
    
    def run_daily_analysis(self):
        """Lance l'analyse quotidienne"""
        logger.info("Début de l'analyse quotidienne")
        
        # Récupération des matchs depuis les deux APIs
        matches = []
        matches.extend(self.get_matches_from_odds_api())
        matches.extend(self.get_matches_from_tennis_api())
        
        # Suppression des doublons
        unique_matches = []
        seen = set()
        for match in matches:
            key = (match['player1'], match['player2'], match['tour'])
            if key not in seen:
                unique_matches.append(match)
                seen.add(key)
        
        logger.info(f"Trouvé {len(unique_matches)} matchs uniques")
        
        # Calcul des différences d'ELO
        analyzed_matches = self.calculate_elo_differences(unique_matches)
        
        # Formatage et envoi du message
        message = self.format_telegram_message(analyzed_matches)
        self.send_telegram_message(message)
        
        logger.info("Analyse terminée")

def main():
    """Fonction principale"""
    bot = TennisEloBot()
    bot.run_daily_analysis()

if __name__ == "__main__":
    main()
