# -*- coding: UTF-8 -*-

import json
import logging
import requests

from datetime import datetime

logger = logging.getLogger(__name__)

EXPIRE_BUFFER_SECONDS = 30

class Pokeslack:
    def __init__(self, rarity_limit, slack_webhook_url):
        self.sent_pokemon = {}
        self.rarity_limit = rarity_limit
        self.slack_webhook_url = slack_webhook_url

    def try_send_pokemon(self, pokemon, position, distance, debug):
        disappear_time = pokemon['disappear_time']
        expires_in = disappear_time - datetime.utcnow()
        rarity = pokemon['rarity']

        if expires_in.total_seconds() < EXPIRE_BUFFER_SECONDS:
            logger.info('skipping pokemon since it expires too soon')
            return

        if rarity < self.rarity_limit:
            logger.info('skipping pokemon since its rarity is too low')
            return

        padded_distance = distance * 1.1
        travel_time = padded_distance / 0.00333333 # assumes 12mph (in miles per second)
        if expires_in.total_seconds() < travel_time:
            logger.info('skipping pokemon since it\'s too far: traveltime=%s for distance=%s', travel_time, distance)
            return

        pokemon_key = pokemon['key']
        if pokemon_key in self.sent_pokemon:
            logger.info('already sent this pokemon to slack')
            return

        from_lure = ', from a lure' if pokemon.get('from_lure', False) else ''
        miles_away = '{:.3f}'.format(distance)

        pokedex_url = 'http://www.pokemon.com/us/pokedex/%s' % pokemon['pokemon_id']
        map_url = 'http://maps.google.com?saddr=%s,%s&daddr=%s,%s&directionsmode=walking' % (position[0], position[1], pokemon['latitude'], pokemon['longitude'])
        min_remaining = int(expires_in.total_seconds() / 60)
        time_remaining = '%s%ss' % ('%dm' % min_remaining if min_remaining > 0 else '', expires_in.seconds - 60 * min_remaining)
        stars = ''.join([':star:' for x in xrange(rarity)])
        message = 'I found a <%s|%s> %s <%s|%s miles away> expiring in %s%s' % (pokedex_url, pokemon['name'], stars, map_url, miles_away, time_remaining, from_lure)
        # bold message if rarity > 4
        if rarity >= 4:
            message = '*%s*' % message

        logging.info('%s: %s', pokemon_key, message)
        if self._send(message):
	    if rarity >= 3:
	    	self._send("<!channel>: Rare Pokemon!! ^")
            self.sent_pokemon[pokemon_key] = True

    def _send(self, message):
        payload = {
            'username': 'Poké Alert!',
            'text': message,
            'icon_emoji': ':ghost:'
        }
        s = json.dumps(payload)
        r = requests.post(self.slack_webhook_url, data=s)
        logger.info('slack post result: %s, %s', r.status_code, r.reason)
        return r.status_code == 200
