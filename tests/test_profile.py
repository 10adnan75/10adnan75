import copy
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update_profile as profile
from wakatime import summarize, TIMEZONE


def pull(number,repo='other/project',state='closed',merged=True):
    return {'number':number,'repository_url':f'https://api.github.com/repos/{repo}',
            'html_url':f'https://github.com/{repo}/pull/{number}',
            'state':state,'title':'Fix <unsafe> [label]',
            'pull_request':{'merged_at':'2026-01-01T00:00:00Z' if merged else None}}


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.today=datetime.now(ZoneInfo(TIMEZONE)).date()
        self.feed={'data':[{'range':{'date':(self.today-timedelta(days=i)).isoformat(),'timezone':TIMEZONE},
                           'grand_total':{'total_seconds':3600 if i==1 else 0}} for i in range(31)]}
        self.pulls=[pull(1),pull(2,state='open',merged=False),pull(3,merged=False),pull(4,repo='10adnan75/test')]

    def fake(self,url):
        if '/search/issues?' in url:
            self.assertIn('is%3Apublic',url)
            return {'total_count':len(self.pulls),'incomplete_results':False,'items':self.pulls}
        if '/repos?' in url:
            return [{'fork':False,'stargazers_count':7},{'fork':True,'stargazers_count':900}]
        if '/users/' in url:return {'followers':5}
        return self.feed

    def test_stat_scopes(self):
        with patch.object(profile,'fetch',self.fake):s=profile.collect()
        self.assertEqual((s['repos'],s['stars'],s['merged_prs'],len(s['external'])),(2,7,2,3))
        self.assertEqual((s['time'],s['active']),('1h 0m',1))

    def test_completed_day_window(self):
        self.feed['data'][0]['grand_total']['total_seconds']=999999
        start,end,days=summarize(self.feed,self.today)
        self.assertEqual(start,self.today-timedelta(days=30))
        self.assertEqual(end,self.today-timedelta(days=1))
        self.assertEqual(sum(s for _,s in days),3600)

    def test_incomplete_or_duplicate_data_rejected(self):
        for rows in [self.feed['data'][:-1],self.feed['data']+[self.feed['data'][1]]]:
            with self.assertRaises(ValueError):summarize({'data':rows},self.today)

    def test_portrait_exact_and_theme_inverted(self):
        original=profile.portrait_lines(False);dark=profile.portrait_lines(True)
        self.assertEqual((len(original),set(map(len,original))),(188,{400}))
        table=str.maketrans(profile.DENSITY,profile.DENSITY[::-1])
        self.assertEqual([line.translate(table) for line in dark],original)

    def test_card_labels_and_theme(self):
        with patch.object(profile,'fetch',self.fake):s=profile.collect()
        for dark,heading in [(True,'#e6edf3'),(False,'#1f2328')]:
            root=ET.fromstring(profile.render(s,dark))
            texts=list(root.iter('{http://www.w3.org/2000/svg}text'))
            visible=[t.text or '' for t in texts]
            self.assertIn('10adnan75',visible);self.assertIn('WakaTime',visible)
            self.assertFalse(any('://' in v for v in visible))
            self.assertFalse(any('Refreshed' in v or 'adnan@' in v for v in visible))
            user=next(t for t in texts if t.text=='10adnan75' and t.get('font-weight')=='700')
            self.assertEqual(user.get('fill'),heading)

    def test_contribution_status_and_escaping(self):
        s=profile.contributions_md(self.pulls[:3])
        for status in ['**merged**','**open**','**closed without merge**']:self.assertIn(status,s)
        self.assertIn('&lt;unsafe&gt; &#91;label&#93;',s)

    def test_readme_update_preserves_surrounding_text(self):
        doc='my intro\n'+profile.START+'old list'+profile.END+'\nmy ending'
        new=profile.refresh_readme(doc,self.pulls)
        self.assertTrue(new.startswith('my intro\n'));self.assertTrue(new.endswith('\nmy ending'))
        self.assertNotIn('old list',new)
        self.assertEqual(profile.refresh_readme(new,self.pulls),new)
        with self.assertRaises(ValueError):profile.refresh_readme('missing markers',self.pulls)

if __name__=='__main__':unittest.main()
