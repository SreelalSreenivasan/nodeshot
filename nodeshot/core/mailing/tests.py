"""
nodeshot.core.mailing unit tests
"""

from django.utils import unittest
from django.test import TestCase

from django.db.models import Q
from django.contrib.auth.models import User, Group
from nodeshot.core.zones.models import Zone
from nodeshot.core.nodes.models import Node
from nodeshot.core.mailing.models import Inward, Outward
from nodeshot.core.mailing.models.choices import GROUPS

class OutwardTest(TestCase):
    
    fixtures = ['groups.json', 'test_users.json', 'test_zones.json', 'test_nodes.json']
    
    def setUp(self):
        # create outward record
        self.message = Outward.objects.create(
            status=0,
            subject='test message',
            message='This is a test message, be sure this text is longer than the minimum required',
            is_scheduled=False,
            is_filtered=False
        )
    
    def test_fixtures(self):
        """
        Tests fixtures have loaded properly.
        """
        zones = Zone.objects.all()
        nodes = Node.objects.all()
        users = User.objects.filter(is_active=True)
        
        self.assertEqual(len(zones), 3)
        self.assertEqual(len(nodes), 6)
        self.assertEqual(len(users), 8)
    
    def test_no_filter(self):
        """
        Test no filtering, send to all
        """
        # count users
        users = User.objects.filter(is_active=True)
        recipients = self.message.get_recipients()
        
        # simplest case: send to all
        # fail if recipient list length and user list length differ
        self.assertEqual(len(recipients), len(users))
        # fail if user emails are not in recipients
        for user in users:
            self.assertTrue(user.email in recipients)
        
    def test_group_filtering(self):
        """
        Test group filtering in multiple combinations
        """
        combinations = [
            '1','2','3','0',
            '1,2','1,3','1,0','2,3','2,0','3,0',
            '1,2,3','1,2,0','1,3,0','2,3,0',
            '1,2,3,0'
        ]
        # prepare record
        message = self.message
        message.is_filtered=True
        message.filters = '1'
        
        for combo in combinations:
            # test multiple groups
            groups = combo.split(',')
            # init empty Q
            q = Q()
            for group in groups:
                # if not superuser case
                if group != '0':
                    # add another group to the Q
                    q = q | Q(groups=group)
                # superuser case
                else:
                    # group 0 wouldn't be correct, therefore we use is_superuser=True 
                    q = q | Q(is_superuser=True)
            # and is_active = True
            q = q & Q(is_active=True)
            # retrieve users
            users = User.objects.filter(q)
            message.groups = combo
            recipients = message.get_recipients()
            # fail if recipient list length and user list length differ
            self.assertEqual(len(recipients), len(users))
            # fail if user emails are not in recipients
            for user in users:
                self.assertTrue(user.email in recipients)
    
    def test_zone_filtering(self):
        """
        Test zone filtering in multiple combinations
        """
        combinations = [
            '1','2','3',
            '1,2','1,3','2,3',
            '1,2,3'
        ]
        # prepare record
        message = self.message
        message.is_filtered=True
        message.filters = '2'
        
        for combo in combinations:
            zones = combo.split(',')
            # init empty Q
            q = Q()
            for zone in zones:
                q = q | Q(zone=zone)
            # retrieve nodes
            nodes = Node.objects.filter(q)
            # zones id list
            message.zones = [int(zone) for zone in zones]
            # retrieve recipients according to model code
            recipients = message.get_recipients()
            # retrieve list of emails
            emails = []
            for node in nodes:
                if not node.user.email in emails:
                    emails += [node.user.email]
            # fail if recipient list length and user list length differ
            self.assertEqual(len(recipients), len(emails))
            # fail if user emails are not in recipients
            for email in emails:
                self.assertTrue(email in recipients)
        
    def test_user_filtering(self):
        """
        Test recipient filtering by user
        """
        combinations = [
            '1','2','3','4','5','6','7','8',
            '1,2','2,3','3,4','5,6'
            '1,2,3','3,4,5','6,7,8'
            '1,2,3,4','5,6,7,8',
            '1,2,3,4,5,6,7,8'
        ]
        # prepare record
        message = self.message
        message.is_filtered=True
        message.filters = '3'
        
        for combo in combinations:
            # users id list
            users_string = combo.split(',')
            user_ids = [int(user) for user in users_string]
            # selected users
            message.users = user_ids
            # retrieve recipients according to the model code
            recipients = message.get_recipients()
            # init empty Q
            q = Q()
            # retrieve users
            for user in user_ids:
                q = q | Q(id=user)
            # only active users
            q = q & Q(is_active=True)
            users = User.objects.filter(q)
            # fail if recipient list length and user list length differ
            self.assertEqual(len(recipients), len(users))
            # fail if user emails are not in recipients
            for user in users:
                self.assertTrue(user.email in recipients)
    
    def test_group_and_zone_filtering(self):
        """
        Test group & zone filtering in multiple combinations
        """
        combinations = [
            { 'groups': '1', 'zones': '1' },
            { 'groups': '2', 'zones': '2' },
            { 'groups': '1,2', 'zones': '1' },
            { 'groups': '1,2,3', 'zones': '1,2' },
            { 'groups': '1,2', 'zones': '1,2,3' },
            { 'groups': '3', 'zones': '1,2,3' }
        ]
        # prepare record
        message = self.message
        message.is_filtered=True
        message.filters = '1,2'
        
        for combo in combinations:
            groups = combo['groups'].split(',')
            zones = combo['zones'].split(',')
            
            # GROUPS
            q1 = Q()
            for group in groups:
                # if not superuser case
                if group != '0':
                    # add another group to the Q
                    q1 = q1 | Q(user__groups=group)
                # superuser case
                else:
                    # group 0 wouldn't be correct, therefore we use is_superuser=True 
                    q1 = q1 | Q(user__is_superuser=True)
            # and is_active = True
            q1 = q1 & Q(user__is_active=True)
            
            # ZONES
            q2 = Q()
            for zone in zones:
                q2 = q2 | Q(zone=zone)
            # retrieve nodes
            nodes = Node.objects.filter(q1 & q2).select_related()
            
            # message group & zones
            message.groups = combo['groups']
            message.zones = [int(zone) for zone in zones]
            
            # retrieve recipients according to model code
            recipients = message.get_recipients()
            # retrieve list of emails
            emails = []
            for node in nodes:
                if not node.user.email in emails:
                    emails += [node.user.email]
            # fail if recipient list length and user list length differ
            self.assertEqual(len(recipients), len(emails))
            # fail if user emails are not in recipients
            for email in emails:
                self.assertTrue(email in recipients)
    
    def test_user_and_zone_filtering(self):
        """
        Test recipient filtering by user & zones
        """
        combinations = [
            { 'users': '1', 'zones': '1' },
            { 'users': '2', 'zones': '2' },
            { 'users': '1,2', 'zones': '1' },
            { 'users': '1,2,3', 'zones': '1,2' },
            { 'users': '1,2', 'zones': '1,2,3' },
            { 'users': '3', 'zones': '1,2,3' },
            { 'users': '3,4,5,6,7', 'zones': '1' }
        ]
        # prepare record
        message = self.message
        message.is_filtered=True
        message.filters = '2,3'
        
        for combo in combinations:
            users = combo['users'].split(',')
            zones = combo['zones'].split(',')
            
            # ZONES
            q1 = Q()
            for zone in zones:
                q1 = q1 | Q(zone=zone)
            # retrieve nodes
            nodes = Node.objects.filter(q1).select_related()
            
            # prepare Q object for user query
            q2 = Q()
            for user in users:
                q2 = q2 | Q(pk=user)
            q2 = q2 & Q(is_active=True)
            
            # message users & zones
            message.users = [int(user) for user in users]
            message.zones = [int(zone) for zone in zones]
            
            # retrieve chosen users
            users = User.objects.filter(q2)
            
            # retrieve recipients according to model code
            recipients = message.get_recipients()
            
            # retrieve list of emails
            emails = []
            for node in nodes:
                if not node.user.email in emails:
                    emails.append(node.user.email)
            
            # add emails of selected users if necessary
            for user in users:
                if not user.email in emails:
                    emails.append(user.email)
            
            # fail if recipient list length and user list length differ
            self.assertEqual(len(recipients), len(emails))
            # fail if user emails are not in recipients
            for email in emails:
                self.assertTrue(email in recipients)