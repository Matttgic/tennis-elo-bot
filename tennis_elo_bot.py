import pandas as pd
import requests
import json
from datetime import datetime, date, timedelta
import time
from typing import Dict, List, Tuple, Optional
import logging
import os

# Configuration depuis les variables d'environnement
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
            logger.info(f"Colonnes ATP trouvées: {list(atp_df.columns)}")
            
            for _, row in atp_df.iterrows():
                if pd.notna(row.get('Player')):
                    player_name = str(row['Player']).lower().strip()
                    
                    # Récupération des ELO par surface avec valeurs par défaut
                    overall_elo = row.get('Elo', 1500)
                    hard_elo = row.get('hElo', overall_elo)
                    clay_elo = row.get('cElo', overall_elo)
                    grass_elo = row.get('gElo', overall_elo)
                    
                    self.atp_elo[player_name] = {
                        'overall': float(overall_elo) if pd.notna(overall_elo) else 1500.0,
                        'hard': float(hard_elo) if pd.notna(hard_elo) else float(overall_elo) if pd.notna(overall_elo) else 1500.0,
                        'clay': float(clay_elo) if pd.notna(clay_elo) else float(overall_elo) if pd.notna(overall_elo) else 1500.0,
                        'grass': float(grass_elo) if pd.notna(grass_elo) else float(overall_elo) if pd.notna(overall_elo) else 1500.0
                    }
            
            # Chargement WTA ELO
            wta_df = pd.read_csv(WTA_ELO_FILE)
            logger.info(f"Colonnes WTA trouvées: {list(wta_df.columns)}")
            
            for _, row in wta_df.iterrows():
                if pd.notna(row.get('Player')):
                    player_name = str(row['Player']).lower().strip()
                    
                    # Récupération des ELO par surface avec valeurs par défaut
                    overall_elo = row.get('Elo', 1500)
                    hard_elo = row.get('hElo', overall_elo)
                    clay_elo = row.get('cElo', overall_elo)
                    grass_elo = row.get('gElo', overall_elo)
                    
                    self.wta_elo[player_name] = {
                        'overall': float(overall_elo) if pd.notna(overall_elo) else 1500.0,
                        'hard': float(hard_elo) if pd.notna(hard_elo) else float(overall_elo) if pd.notna(overall_elo) else 1500.0,
                        'clay': float(clay_elo) if pd.notna(clay_elo) else float(overall_elo) if pd.notna(overall_elo) else 1500.0,
                        'grass': float(grass_elo) if pd.notna(grass_elo) else float(overall_elo) if pd.notna(overall_elo) else 1500.0
                    }
            
            logger.info(f"Chargé {len(self.atp_elo)} joueurs ATP et {len(self.wta_elo)} joueuses WTA")
            
            # Debug: afficher quelques exemples
            if self.atp_elo:
                first_atp = list(self.atp_elo.items())[0]
                logger.info(f"Exemple ATP: {first_atp[0]} -> {first_atp[1]}")
            
            if self.wta_elo:
                first_wta = list(self.wta_elo.items())[0]
                logger.info(f"Exemple WTA: {first_wta[0]} -> {first_wta[1]}")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données ELO: {e}")
            import traceback
            logger.error(f"Traceback complet: {traceback.format_exc()}")
    
    def normalize_player_name(self, name: str) -> str:
        """Normalise le nom du joueur pour la recherche"""
        if not name:
            return ""
        return name.lower().strip().replace(".", "").replace("-", " ").replace("'", "")
    
    def find_player_elo(self, player_name: str, tour: str) -> Dict:
        """Trouve l'ELO d'un joueur avec recherche flexible"""
        if not player_name:
            return {'hard': 1500.0, 'clay': 1500.0, 'grass': 1500.0, 'overall': 1500.0}
            
        normalized_name = self.normalize_player_name(player_name)
        elo_data = self.atp_elo if tour.upper() == 'ATP' else self.wta_elo
        
        # 1. Recherche directe
        if normalized_name in elo_data:
            logger.debug(f"Trouvé {player_name} par recherche directe")
            return elo_data[normalized_name]
        
        # 2. Recherche approximative (nom contenu)
        for stored_name, elo in elo_data.items():
            if normalized_name in stored_name or stored_name in normalized_name:
                logger.debug(f"Trouvé {player_name} -> {stored_name} par recherche approximative")
                return elo
        
        # 3. Recherche par mots (nom et prénom)
        name_parts = [part for part in normalized_name.split() if len(part) > 1]
        if len(name_parts) >= 2:
            for stored_name, elo in elo_data.items():
                if all(part in stored_name for part in name_parts):
                    logger.debug(f"Trouvé {player_name} -> {stored_name} par recherche par mots")
                    return elo
        
        # 4. Recherche partielle sur le nom de famille (dernier mot)
        if name_parts:
            last_name = name_parts[-1]
            if len(last_name) > 3:  # Éviter les correspondances trop courtes
                for stored_name, elo in elo_data.items():
                    if last_name in stored_name or any(last_name in part for part in stored_name.split()):
                        logger.debug(f"Trouvé {player_name} -> {stored_name} par nom de famille")
                        return elo
        
        # ELO par défaut si joueur non trouvé
        logger.warning(f"Joueur non trouvé: {player_name} ({tour}) - utilisation ELO par défaut")
        return {'hard': 1500.0, 'clay': 1500.0, 'grass': 1500.0, 'overall': 1500.0}
    
    def get_surface_from_tournament(self, tournament_name: str) -> str:
        """Détermine la surface selon le nom du tournoi"""
        if not tournament_name:
            return 'hard'
            
        tournament_lower = tournament_name.lower()
        
        # Tournois sur terre battue
        clay_keywords = [
            'roland', 'garros', 'french', 'rome', 'madrid', 'monte carlo', 'barcelona',
            'clay', 'terre', 'battue', 'hamburg', 'bastad', 'gstaad', 'umag',
            'bucharest', 'marrakech', 'estoril', 'munich', 'houston'
        ]
        
        # Tournois sur gazon
        grass_keywords = [
            'wimbledon', 'queens', 'halle', 'eastbourne', 'grass', 'gazon',
            'hertogenbosch', 'mallorca', 'bad homburg', 'newport'
        ]
        
        if any(keyword in tournament_lower for keyword in clay_keywords):
            return 'clay'
        elif any(keyword in tournament_lower for keyword in grass_keywords):
            return 'grass'
        else:
            return 'hard'  # Surface par défaut (dur)
    
    def get_matches_from_odds_api(self) -> List[Dict]:
        """Récupère les matchs depuis l'API Odds - Version corrigée"""
        matches = []
        
        if ODDS_API_KEY == 'VOTRE_ODDS_API_KEY':
            logger.warning("Clé API Odds non configurée")
            return matches
        
        try:
            # Utiliser l'endpoint 'upcoming' pour les sports de tennis disponibles
            base_url = "https://api.the-odds-api.com/v4/sports"
            
            # D'abord, récupérer la liste des sports disponibles
            sports_url = f"{base_url}?apiKey={ODDS_API_KEY}"
            logger.info("Récupération des sports disponibles...")
            
            sports_response = requests.get(sports_url, timeout=10)
            
            if sports_response.status_code == 200:
                sports_data = sports_response.json()
                tennis_sports = [sport for sport in sports_data if 'tennis' in sport.get('key', '').lower()]
                
                logger.info(f"Sports de tennis trouvés: {[sport['key'] for sport in tennis_sports]}")
                
                # Pour chaque sport de tennis, récupérer les matchs
                for sport in tennis_sports:
                    sport_key = sport['key']
                    odds_url = f"{base_url}/{sport_key}/odds/?apiKey={ODDS_API_KEY}&regions=us&markets=h2h&dateFormat=iso"
                    
                    logger.info(f"Récupération des matchs pour {sport_key}...")
                    
                    odds_response = requests.get(odds_url, timeout=10)
                    
                    if odds_response.status_code == 200:
                        odds_data = odds_response.json()
                        logger.info(f"Reçu {len(odds_data)} matchs pour {sport_key}")
                        
                        for match in odds_data:
                            # Vérifier si le match est aujourd'hui ou dans les prochaines 24h
                            commence_time = match.get('commence_time', '')
                            if self.is_within_next_24h(commence_time):
                                # Déterminer si c'est ATP ou WTA
                                tour = 'ATP' if 'atp' in sport_key.lower() else 'WTA' if 'wta' in sport_key.lower() else 'Unknown'
                                
                                matches.append({
                                    'player1': match.get('home_team', ''),
                                    'player2': match.get('away_team', ''),
                                    'tour': tour,
                                    'tournament': sport.get('title', 'Unknown'),
                                    'commence_time': commence_time
                                })
                    else:
                        logger.warning(f"Erreur pour {sport_key}: {odds_response.status_code}")
            else:
                logger.error(f"Erreur récupération sports: {sports_response.status_code}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération depuis Odds API: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        logger.info(f"Total matchs Odds API: {len(matches)}")
        return matches
    
    def get_matches_from_tennis_api(self) -> List[Dict]:
        """Récupère les matchs depuis Tennis API"""
        matches = []
        
        if TENNIS_API_KEY == 'VOTRE_TENNIS_API_KEY':
            logger.warning("Clé Tennis API non configurée")
            return matches
        
        try:
            today_str = date.today().strftime('%Y-%m-%d')
            url = f"https://api.api-tennis.com/tennis/?met=Matchs&APIkey={TENNIS_API_KEY}&date={today_str}"
            
            logger.info(f"Récupération des matchs depuis Tennis API pour {today_str}...")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and data['result']:
                    logger.info(f"Reçu {len(data['result'])} matchs de Tennis API")
                    
                    for match in data['result']:
                        # Déterminer le tour (ATP/WTA) basé sur le nom de la ligue
                        league_name = match.get('league_name', '').upper()
                        tour = 'ATP' if 'ATP' in league_name or 'MEN' in league_name else 'WTA'
                        
                        matches.append({
                            'player1': match.get('match_hometeam_name', ''),
                            'player2': match.get('match_awayteam_name', ''),
                            'tour': tour,
                            'tournament': match.get('league_name', 'Unknown'),
                            'commence_time': match.get('match_date', '')
                        })
                else:
                    logger.info("Aucun résultat trouvé dans Tennis API")
            else:
                logger.error(f"Erreur Tennis API: {response.status_code} - {response.text}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération depuis Tennis API: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        logger.info(f"Total matchs Tennis API: {len(matches)}")
        return matches
    
    def is_within_next_24h(self, date_string: str) -> bool:
        """Vérifie si la date est dans les prochaines 24 heures"""
        if not date_string:
            return False
            
        try:
            # Parser la date ISO
            if date_string.endswith('Z'):
                match_datetime = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            else:
                match_datetime = datetime.fromisoformat(date_string)
            
            # Obtenir l'heure actuelle
            now = datetime.now(match_datetime.tzinfo)
            
            # Vérifier si c'est dans les prochaines 24h
            time_diff = match_datetime - now
            return timedelta(hours=0) <= time_diff <= timedelta(hours=24)
            
        except Exception as e:
            logger.debug(f"Impossible de parser la date '{date_string}': {e}")
            return False
    
    def is_today(self, date_string: str) -> bool:
        """Vérifie si la date correspond à aujourd'hui"""
        if not date_string:
            return False
            
        try:
            # Différents formats de date possibles
            formats = [
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    if 'T' in date_string and date_string.endswith('Z'):
                        match_date = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ').date()
                    else:
                        match_date = datetime.strptime(date_string, fmt).date()
                    
                    return match_date == date.today()
                except ValueError:
                    continue
            
            # Fallback: essayer de parser avec fromisoformat
            match_date = datetime.fromisoformat(date_string.replace('Z', '+00:00')).date()
            return match_date == date.today()
            
        except Exception as e:
            logger.debug(f"Impossible de parser la date '{date_string}': {e}")
            return False
    
    def calculate_elo_differences(self, matches: List[Dict]) -> List[Dict]:
        """Calcule les différences d'ELO pour chaque match"""
        match_analyses = []
        
        for match in matches:
            try:
                if not match.get('player1') or not match.get('player2'):
                    logger.warning(f"Match avec joueurs manquants: {match}")
                    continue
                
                surface = self.get_surface_from_tournament(match.get('tournament', ''))
                
                player1_elo_data = self.find_player_elo(match['player1'], match.get('tour', 'ATP'))
                player2_elo_data = self.find_player_elo(match['player2'], match.get('tour', 'ATP'))
                
                player1_elo = player1_elo_data.get(surface, player1_elo_data.get('overall', 1500))
                player2_elo = player2_elo_data.get(surface, player2_elo_data.get('overall', 1500))
                
                elo_diff = abs(player1_elo - player2_elo)
                
                match_analyses.append({
                    'player1': match['player1'],
                    'player1_elo': player1_elo,
                    'player2': match['player2'],
                    'player2_elo': player2_elo,
                    'surface': surface,
                    'elo_difference': elo_diff,
                    'tour': match.get('tour', 'Unknown'),
                    'tournament': match.get('tournament', 'Unknown'),
                    'commence_time': match.get('commence_time', '')
                })
                
            except Exception as e:
                logger.error(f"Erreur calcul ELO pour {match}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Tri par différence d'ELO décroissante
        sorted_matches = sorted(match_analyses, key=lambda x: x['elo_difference'], reverse=True)
        logger.info(f"Analysé {len(sorted_matches)} matchs avec succès")
        
        return sorted_matches
    
    def format_telegram_message(self, matches: List[Dict]) -> str:
        """Formate le message pour Telegram"""
        if not matches:
            return f"🎾 Aucun match trouvé pour aujourd'hui ({date.today().strftime('%d/%m/%Y')})"
        
        message = f"🎾 **MATCHS TENNIS DU {date.today().strftime('%d/%m/%Y')}**\n"
        message += f"📊 Classés par écart d'ELO (du plus grand au plus petit)\n\n"
        
        for i, match in enumerate(matches[:20], 1):  # Limiter à 20 matchs pour éviter les messages trop longs
            higher_elo_player = match['player1'] if match['player1_elo'] > match['player2_elo'] else match['player2']
            lower_elo_player = match['player2'] if match['player1_elo'] > match['player2_elo'] else match['player1']
            higher_elo = max(match['player1_elo'], match['player2_elo'])
            lower_elo = min(match['player1_elo'], match['player2_elo'])
            
            # Icône selon l'écart
            if match['elo_difference'] > 200:
                icon = "🔥"  # Très gros écart
            elif match['elo_difference'] > 100:
                icon = "⚡"  # Gros écart
            elif match['elo_difference'] > 50:
                icon = "📈"  # Écart moyen
            else:
                icon = "⚖️"  # Petit écart
            
            message += f"{icon} **Match {i}** ({match['tour']})\n"
            message += f"🏆 {higher_elo_player} ({higher_elo:.0f})\n"
            message += f"🆚 {lower_elo_player} ({lower_elo:.0f})\n"
            message += f"🎯 Surface: {match['surface'].title()}\n"
            message += f"📈 Écart ELO: **{match['elo_difference']:.0f}**\n"
            message += f"🏟️ {match['tournament']}\n\n"
        
        if len(matches) > 20:
            message += f"... et {len(matches) - 20} autres matchs\n\n"
        
        message += f"🤖 Analyse basée sur {len(self.atp_elo)} joueurs ATP et {len(self.wta_elo)} joueuses WTA"
        
        return message
    
    def send_telegram_message(self, message: str):
        """Envoie le message sur Telegram"""
        if TELEGRAM_BOT_TOKEN == 'VOTRE_BOT_TOKEN':
            logger.warning("Token Telegram non configuré - affichage du message:")
            print("\n" + "="*50)
            print("MESSAGE TELEGRAM:")
            print("="*50)
            print(message)
            print("="*50)
            return
        
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            
            # Diviser le message si trop long (limite Telegram: 4096 caractères)
            max_length = 4000  # Marge de sécurité
            
            if len(message) > max_length:
                # Diviser le message en parties
                parts = []
                current_part = ""
                
                for line in message.split('\n'):
                    if len(current_part) + len(line) + 1 > max_length:
                        if current_part:
                            parts.append(current_part)
                        current_part = line
                    else:
                        current_part += ('\n' if current_part else '') + line
                
                if current_part:
                    parts.append(current_part)
                
                logger.info(f"Message divisé en {len(parts)} parties")
                
                for i, part in enumerate(parts, 1):
                    payload = {
                        'chat_id': TELEGRAM_CHAT_ID,
                        'text': f"[{i}/{len(parts)}]\n{part}" if len(parts) > 1 else part,
                        'parse_mode': 'Markdown'
                    }
                    
                    response = requests.post(url, json=payload)
                    
                    if response.status_code == 200:
                        logger.info(f"Partie {i}/{len(parts)} envoyée avec succès")
                    else:
                        logger.error(f"Erreur envoi partie {i}: {response.text}")
                    
                    if i < len(parts):  # Pause entre les messages sauf pour le dernier
                        time.sleep(2)
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
                    logger.error(f"Erreur envoi Telegram: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message Telegram: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def run_daily_analysis(self):
        """Lance l'analyse quotidienne"""
        logger.info("="*50)
        logger.info("DÉBUT DE L'ANALYSE QUOTIDIENNE")
        logger.info("="*50)
        
        # Vérifier que les clés API sont configurées
        api_configured = False
        if ODDS_API_KEY != 'VOTRE_ODDS_API_KEY':
            logger.info("✓ Clé API Odds configurée")
            api_configured = True
        else:
            logger.warning("✗ Clé API Odds NON configurée")
            
        if TENNIS_API_KEY != 'VOTRE_TENNIS_API_KEY':
            logger.info("✓ Clé Tennis API configurée")
            api_configured = True
        else:
            logger.warning("✗ Clé Tennis API NON configurée")
        
        if not api_configured:
            logger.error("Aucune API configurée - impossible de récupérer les matchs")
            message = "⚠️ **ERREUR CONFIGURATION**\n\n"
            message += "Aucune clé API n'est configurée. Veuillez configurer au moins une des clés suivantes dans les secrets GitHub:\n"
            message += "- ODDS_API_KEY\n"
            message += "- TENNIS_API_KEY\n\n"
            message += "Sans ces clés, le bot ne peut pas récupérer les matchs du jour."
            self.send_telegram_message(message)
            return
        
        # Récupération des matchs depuis les APIs disponibles
        all_matches = []
        
        # API Odds
        if ODDS_API_KEY != 'VOTRE_ODDS_API_KEY':
            odds_matches = self.get_matches_from_odds_api()
            all_matches.extend(odds_matches)
        
        # Tennis API
        if TENNIS_API_KEY != 'VOTRE_TENNIS_API_KEY':
            tennis_matches = self.get_matches_from_tennis_api()
            all_matches.extend(tennis_matches)
        
        logger.info(f"Total matchs récupérés: {len(all_matches)}")
        
        # Suppression des doublons basée sur les joueurs et le tour
        unique_matches = []
        seen = set()
        
        for match in all_matches:
            # Créer une clé unique pour détecter les doublons
            key1 = (
                self.normalize_player_name(match.get('player1', '')),
                self.normalize_player_name(match.get('player2', '')),
                match.get('tour', 'Unknown')
            )
            key2 = (
                self.normalize_player_name(match.get('player2', '')),
                self.normalize_player_name(match.get('player1', '')),
                match.get('tour', 'Unknown')
            )
            
            if key1 not in seen and key2 not in seen:
                unique_matches.append(match)
                seen.add(key1)
                seen.add(key2)
        
        logger.info(f"Matchs uniques après suppression des doublons: {len(unique_matches)}")
        
        if not unique_matches:
            logger.info("Aucun match trouvé pour aujourd'hui")
            message = f"🎾 Aucun match de tennis trouvé pour aujourd'hui ({date.today().strftime('%d/%m/%Y')})\n\n"
            message += "Vérifiez les APIs ou attendez les prochains matchs ! 🕐"
            self.send_telegram_message(message)
            return
        
        # Calcul des différences d'ELO
        logger.info("Calcul des différences d'ELO...")
        analyzed_matches = self.calculate_elo_differences(unique_matches)
        
        if not analyzed_matches:
            logger.warning("Aucun match analysé avec succès")
            message = f"⚠️ Erreur lors de l'analyse des matchs du {date.today().strftime('%d/%m/%Y')}\n\n"
            message += "Les données ELO n'ont pas pu être récupérées correctement."
            self.send_telegram_message(message)
            return
        
        # Formatage et envoi du message
        logger.info("Formatage du message Telegram...")
        telegram_message = self.format_telegram_message(analyzed_matches)
        
        logger.info("Envoi du message sur Telegram...")
        self.send_telegram_message(telegram_message)
        
        logger.info("="*50)
        logger.info("ANALYSE QUOTIDIENNE TERMINÉE")
        logger.info(f"- {len(unique_matches)} matchs trouvés")
        logger.info(f"- {len(analyzed_matches)} matchs analysés avec succès")
        logger.info("="*50)


def main():
    """Fonction principale"""
    try:
        logger.info("Initialisation du Tennis ELO Bot...")
        bot = TennisEloBot()
        
        logger.info("Lancement de l'analyse quotidienne...")
        bot.run_daily_analysis()
        
        logger.info("Script terminé avec succès !")
        
    except Exception as e:
        logger.error(f"Erreur fatale dans le script principal: {e}")
        import traceback
        logger.error(f"Traceback complet: {traceback.format_exc()}")
        
        # Tentative d'envoi d'un message d'erreur si possible
        try:
            if TELEGRAM_BOT_TOKEN != 'VOTRE_BOT_TOKEN':
                error_message = f"🚨 **ERREUR TENNIS BOT** 🚨\n\n"
                error_message += f"Le script a rencontré une erreur fatale:\n"
                error_message += f"`{str(e)}`\n\n"
                error_message += f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {
                    'chat_id': TELEGRAM_CHAT_ID,
                    'text': error_message,
                    'parse_mode': 'Markdown'
                }
                
                requests.post(url, json=payload)
        except:
            pass  # Ignore les erreurs lors de l'envoi du message d'erreur
        
        raise


if __name__ == "__main__":
    main()
