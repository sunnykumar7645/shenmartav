# -*- coding: utf-8 -*-

"""
Model Representative

Depends on popit
"""
__docformat__ = 'epytext en'

import datetime
from operator import itemgetter
from django.conf import settings
from django.db import models
from django.db.models import Q

try:
    # SIGH! this is Django 1.4 which spits out warnings otherwise
    # Django 1.4. was necessary to fix an issue with PostGIS
    # an issue that occurred with the introduction of unit tests.
    from django.utils.timezone import utc
except ImportError:
    utc = None
from django.utils.translation import activate, get_language, ugettext as _
from django.template.defaultfilters import slugify
from sorl.thumbnail.fields import ImageWithThumbnailsField

from shenmartav import glt
from apps.popit.models import Person, Organisation
from unidecode import unidecode


#: minimum length of (representative's) name
NAME_MINLEN = 4


class Term(models.Model):
    """A Term during which Representatives are part of a Unit."""
    #: start of the term
    start = models.DateField(blank=False, help_text=_('When term started'))
    #: end of the term
    end = models.DateField(blank=False, help_text=_('When term started'))
    #: name of the term
    name = models.CharField(max_length=255, blank=False, help_text=_('Name of this term'))

    def __unicode__(self):
        return u'%s (%s - %s)' % (self.name, self.start, self.end)


class Party(Organisation):
    """A political party in a unit, as used in the template representative/unit.html"""
    #: acronym of this party
    acronym = models.CharField(max_length=16, blank=False, null=False,
                               help_text=_('Acronym of this Party'))
    #: url of this representative
    url = models.TextField(blank=True, help_text=_('URL of this Party'))
    #: party logo
    logo = ImageWithThumbnailsField(upload_to='parties',
                                    thumbnail={'size': (100, 84), 'options': ('crop',)},
                                    blank=True, null=True, help_text=_('Party logo'))


class Cabinet(models.Model):
    """
    Cabinet for factions. I.e Majority, Minority etc.
    """
    name = models.CharField(max_length=255, blank=False, help_text=_('Name of the cabinet'))

    short = models.CharField(max_length=32, blank=False, null=False,
                             help_text=_('Short Name of the cabinet, as used in e.g. CSS'))
    position = models.IntegerField(default=None, blank=True, null=True)

    class Meta(object):
        ordering = ['position']

    def save(self, *args, **kwargs):
        model = self.__class__

        if self.position is None:
            last_position = model.objects.all().order_by('position')[0].position
            if last_position is None:
                self.position = 0
            else:
                self.position = last_position + 1

        return super(Cabinet, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'%s' % self.name


class Faction(models.Model):
    """
    Faction for representatives
    """
    name = models.CharField(max_length=255, blank=False, help_text=_('Name of the faction'))

    short = models.CharField(max_length=32, blank=False, help_text=_('Short Name of the faction, as used in e.g. CSS'))

    cabinet = models.ForeignKey(Cabinet, blank=False, null=True,
                                related_name='faction', help_text=_('Cabinet this faction belongs to'))

    def __unicode__(self):
        return u'%s' % self.name


class Unit(models.Model):
    """A unit/house, like Parliament or Tbilisi City Assembly."""
    #: name of the unit
    name = models.CharField(max_length=255, blank=False, null=False,
                            help_text=_('Name of the Unit.'))
    #: short name of the unit, as used in css, etc.
    short = models.CharField(max_length=32, blank=False, help_text=_('Short Name of the Unit, as used in e.g. CSS'))
    #: parties of this unit
    parties = models.ManyToManyField(Party, related_name='unit',
                                     help_text=_('Parties in this unit'))
    #: unit's active term
    active_term = models.ForeignKey(Term, blank=False, null=True,
                                    related_name='unit_active',
                                    help_text=_('The Unit\'s active term.'))
    #: unit's inactive terms
    inactive_terms = models.ManyToManyField(Term, blank=True,
                                            related_name='unit_inactive',
                                            help_text=_('Past or just inactive terms served in this Unit.'))

    def __unicode__(self):
        return u'%s' % self.name


class ParliamentManager(models.Manager):
    """Manager to return Georgian Parliament representatives in active term."""

    def get_query_set(self):
        """
        Filters queryset to results only in parliament
        @return: Queryset of all active representatives in parliament
        """
        parliament = Unit.objects.get(pk=1)
        return parliament.active_term.representatives.all()


class TbilisiManager(models.Manager):
    """Manager to return Tbilisi City Hall representatives in active term."""

    def get_query_set(self):
        """
        Filters queryset results only to tbilisi Unit.
        @return: Queryset of all active representatives in tbilisi unit
        """
        cityhall = Unit.objects.get(pk=2)
        return cityhall.active_term.representatives.all()


class AjaraManager(models.Manager):
    """Manager to return Ajaran Supreme Council representatives in active term."""

    def get_query_set(self):
        """
        Filters queryset results only to Ajara unit.
        @return: Queryset of all active representatives in Ajara unit
        """
        supremecouncil = Unit.objects.get(pk=3)
        return supremecouncil.active_term.representatives.all()


GENDER_CHOICES = (
    (0, _('male')),
    (1, _('female')),
    (2, _('other')),
)


class Representative(Person):
    """A representative derived from popit.Person."""
    #: personal photo
    photo = ImageWithThumbnailsField(upload_to='representatives',
                                     thumbnail={'size': (200, 168), 'options': ('crop',)},
                                     blank=True, null=True, help_text=_('Personal Photo'))
    #: party membership
    party = models.ForeignKey(Party, related_name='representatives', blank=True, null=True,
                              help_text=_('Party Membership'))
    #: unit membership
    unit = models.ForeignKey(Unit, related_name='representatives', blank=True, null=True,
                             help_text=_('Unit Membership'))
    #: committee membership
    committee = models.TextField(blank=True, help_text=_('Committee Membership'))
    #: faction membership
    faction = models.ForeignKey(Faction, related_name='representatives', blank=True, null=True,
                                help_text=_('Faction membership'))

    #: is majoritarian?
    is_majoritarian = models.BooleanField(blank=True, default=False,
                                          help_text=_('Is Majoritarian?'))
    #: electoral district
    electoral_district = models.TextField(blank=True, help_text=_('Electoral District (if Majoritarian)'))
    #: date elected
    elected = models.TextField(blank=True, help_text=_('Date Elected'))
    #: place of birth
    pob = models.TextField(blank=True, help_text=_('Place of Birth'))
    #: family status
    family_status = models.TextField(blank=True, null=True,
                                     help_text=_('Family Status'))
    #: education
    education = models.TextField(blank=True, help_text=_('Education'))
    #: contact, address and phone number
    contact_address_phone = models.TextField(blank=True, help_text=_('Contact Address / Phone Number'))
    #: salary
    salary = models.FloatField(default=0, blank=True, null=True,
                               help_text=_('== Wages'))
    #: other income
    other_income = models.FloatField(default=0, blank=True, null=True,
                                     help_text=_('== Entrepreneurial Income'))
    #: expenses
    expenses = models.TextField(blank=True, help_text=_('Expenses'))
    #: property & assets
    property_assets = models.TextField(blank=True, help_text=_('Property & Assets'))
    #: percentage of questions answered on shenmartav.ge
    answered = models.FloatField(default=0, blank=True, null=True,
                                 help_text=_('Percentage of Answered Questions on chemiparlamenti.ge'))
    #: gender of the representative
    gender = models.IntegerField(default=0, choices=GENDER_CHOICES, blank=True, null=True,
                                 help_text=_('Gender of the Representative'))
    #: terms of the representative
    terms = models.ManyToManyField(Term, blank=True, null=True,
                                   related_name='representatives',
                                   help_text=_('Terms during which Representative was part of a Unit.'))
    #: asset declaration id submitted by representative
    declaration_id = models.IntegerField(default=0, blank=True, null=True, help_text=_('Asset Declaration Id'))
    #: submission date - asset declaration
    submission_date = models.DateField(blank=True, null=True, help_text=_('Asset Declaration submission date'))
    #: Representative's entrepreneurial salary
    entrepreneurial_salary = models.FloatField(default=0, blank=True, null=True,
                                               help_text=_('Representative entrepreneurial salary'))
    #: Representative's work income
    main_salary = models.FloatField(default=0, blank=True, null=True, help_text=_('Representative income'))

    #: managers
    objects = models.Manager()
    parliament = ParliamentManager()
    tbilisi = TbilisiManager()
    ajara = AjaraManager()

    @classmethod
    def _filter_name(cls, name):
        """
        Filter out multiple names in provided name. For example: "Giorgi (gia) Giorgadze" will be converted to
        "Giorgi Giorgadze"
        @param name: Representative name with possible multiple names
        @return: Filtered out representative name with only one name
        """
        name_dict = name.split()
        full_name = ""

        for name in name_dict:
            if "(" not in name:
                full_name += ' ' + name

        return full_name.strip()

    @classmethod
    def _find_firstname_first(cls, name):
        """Find a representative with given name firstname first.

        @param name: name of the representative
        @type name: str
        @return: representative matching the name
        @rtype: representative.Representative
        """
        firstname_first = glt.firstname_first(name)

        # Find rep whose name starts with Firstname and ends with lastname.
        # This is good for people whose name contains different letters in the end or missing "i" etc.
        representative = cls.objects.filter(
            Q(names__name_ka__startswith=firstname_first.split()[0]) & # firstname
            Q(names__name_ka__endswith=firstname_first.split()[-1]) | # lastname

            Q(names__name_en__startswith=firstname_first.split()[0]) &
            Q(names__name_en__endswith=firstname_first.split()[-1]) |

            Q(names__name__icontains=firstname_first)
        )

        try:
            return representative[0]
        except IndexError:
            return None

    @classmethod
    def _find_lastname_first(cls, name):
        """Find a representative with given name lastname first.

        @param name: name of the representative
        @type name: str
        @return: representative matching the name
        @rtype: representative.Representative
        """

        lastname_first = glt.lastname_first(name)

        # Find rep whose name starts with Firstname and ends with lastname.
        # This is good for people whose name contains different letters in the end or missing "i" etc.
        representative = cls.objects.filter(
            Q(names__name_ka__startswith=lastname_first.split()[0]) & # lastname
            Q(names__name_ka__endswith=lastname_first.split()[1]) | # firstname

            Q(names__name_en__startswith=lastname_first.split()[0]) &
            Q(names__name_en__endswith=lastname_first.split()[1]) |

            Q(names__name__icontains=lastname_first)
        )

        try:
            return representative[0]
        except IndexError:
            return None

    @classmethod
    def _find_startswith(cls, start):
        """Find a representative whose name starts with given start.

        @param start: first charactes of representative's name
        @type start: str
        @return: representative whose name starts with given start
        @rtype: representative.Representative
        """
        if len(start) < NAME_MINLEN:
            return None

        startswith = start[:NAME_MINLEN]
        representative = cls.objects.filter(
            Q(names__name_ka__istartswith=startswith) |
            Q(names__name_en__istartswith=startswith) |
            Q(names__name__istartswith=startswith)
        )

        try:
            return representative[0]
        except IndexError:
            return None

    @classmethod
    def find(cls, name, first=None):
        """Find a representative with given name.

        @param name: name of the representative
        @type name: unicode
        @param first: Set to 'lastname' if first word in input name is lastname and 'firstname' if it's firstname
        @type first: str
        @return: representative matching the name
        @rtype: representative.Representative
        """
        name = cls._filter_name(name)

        if len(name) < NAME_MINLEN:
            representative = None

        elif first == 'lastname':
            representative = cls._find_firstname_first(name)

        elif first == 'firstname':
            representative = cls._find_lastname_first(name)

        else:
            representative = cls._find_lastname_first(name)
            if representative is None:
                representative = cls._find_firstname_first(name)

        if representative:
            return representative
        else:
            representative = cls.objects.filter(
                Q(names__name_ka__icontains=name) |
                Q(names__name_en__icontains=name) |
                Q(names__name__icontains=name)
            )
            if representative:
                return representative
            else:
                return None

    @classmethod
    def by_lastname_firstname_first(cls, representatives=None):
        """Sort given representatives by lastname and show firstname first.

        @param representatives: queryset of representatives to sort, using all() if None
        @type representatives: QuerySet
        @return: sorted list by lastname, including 'firstname_first'
        @rtype: [{
            'pk': int, 'slug': str, 'party__acronym': str,
            'is_majoritarian': bool, 'photo': str,
            'names__name': str, 'names__name_$lang': str,
            'firstname_first': str
        }]
        """
        if representatives is None:
            representatives = cls.objects.all()

        by_lastname = []
        # losing language abstraction, gaining massive reduction in db queries
        name_lang = 'names__name_' + get_language()[:2]
        reps = representatives.values('pk', 'slug',
                                      'party__acronym', 'faction__short', 'is_majoritarian', 'photo',
                                      'names__name', name_lang)
        for r in reps:
            try:
                lastname = r[name_lang].split()[-1]
                r['firstname_first'] = r[name_lang]
            except AttributeError:
                if r['names__name'] is not None:
                    lastname = r['names__name'].split()[-1]
                else:
                    lastname = ''

                r['firstname_first'] = r['names__name']
            by_lastname.append((lastname, r))

        return [p[1] for p in sorted(by_lastname, key=itemgetter(0))]
        #return [by_lastname[key] for key in sorted(by_lastname.keys())]

    @classmethod
    def by_lastname_lastname_first(cls, representatives=None, choices=False):
        """Sort given representatives by lastname and show lastname first.

        @param representatives: queryset of representatives to sort, using all() if None
        @type representatives: QuerySet
        @param choices: if list suitable for form choices should be returned
        @type choices: bool
        @return: sorted list by lastname, including 'lastname_first'
        @rtype: [{
            'pk': int, 'slug': str,
            'names_name': str, 'names__name_$lang': str,
            'lastname_first': str
        }]

        """
        if representatives is None:
            representatives = cls.objects.all()

        by_lastname = []
        # losing language abstraction, gaining massive reduction in db queries
        name_lang = 'names__name_' + get_language()[:2]
        reps = representatives.values('pk', 'slug', 'names__name', name_lang)
        for r in reps:
            try:
                splitname = r[name_lang].split()
            except AttributeError:
                splitname = []
                if r['names__name'] is not None:
                    splitname = r['names__name'].split()

            if splitname != []:
                lastname = splitname.pop()
            else:
                lastname = ''
                
            r['lastname_first'] = lastname + ' ' + ' '.join(splitname)
            by_lastname.append((lastname, r))

        if choices:
            return [
                (p[1]['pk'], p[1]['lastname_first'])
                for p in sorted(by_lastname, key=itemgetter(0))
            ]
        else:
            return [p[1] for p in sorted(by_lastname, key=itemgetter(0))]

    @property
    def income(self):
        """
        Income of representative
        @return: Dictionary with income values
        @rtype: {
        'total' : int,
        'base' : int
        'entrepreneurial': int,
        'main': int,
        'incomeyear': int,
        'latestsubmissionyear': int,
        'declarationid': int
        }
        """
        #try:
        #    base = int(settings.BASE_INCOME[self.unit.short])
        #except (AttributeError, KeyError, ValueError):
        #    base = 0
        # New MPs haven't been in Parliament for more than one year,
        # so can't calculate their base salary accurately.
        base = 0
        try:
            mpincome = self.declarationtotalincome.all()[0]
        except IndexError:
            mpincome = 0
        
        main = self.main_salary
        entrepreneurial = self.entrepreneurial_salary

        incomeyear = 0
        submissionyear = 0
        if self.submission_date:
            incomeyear = self.submission_date.year
            submissionyear = self.submission_date.year
         
        declarationid = self.declaration_id
        
        return {
            'total': int(main + entrepreneurial),
            'base': base,
            'entrepreneurial': entrepreneurial,
            'main': main,
            'incomeyear': incomeyear,
            'latestsubmissionyear': submissionyear,
            'declarationid': declarationid,
        }

    @property
    def assets_list(self):
        """
        List of assets of representative
        @return: List with assets
        @rtype: list
        """
        if self.property_assets:
            return self.property_assets.split(';')
        return None

    def save(self, *args, **kwargs):
        """
        Update save method in order to enforce slug in default language
        @param args:
        @param kwargs:
        @return:
        """
        # enforce rewriting of slug in default language
        lang = get_language()
        activate(settings.LANGUAGE_CODE)
        if isinstance(self.name, basestring):
            self.slug = slugify(unidecode(self.name))
        elif self.name.name:
            self.slug = slugify(unidecode(self.name.name))
        else:
            self.slug = ''
        activate(lang)

        super(Representative, self).save(*args, **kwargs)


class AdditionalInformation(models.Model):
    """
    Additional information for representative
    """
    #: representative this info belongs to
    representative = models.ForeignKey(Representative,
                                       related_name='additional_information', null=True,
                                       help_text=_('Representative'))
    #: value of this info
    value = models.TextField(blank=True, help_text=_('Additional Information'))

    def __unicode__(self):
        return u'%s: %s' % (str(self.representative.name), self.value)


''' original version  with raw HTML
class FamilyIncome (models.Model):
    """A list of details regarding MP's family income"""
    #: ID of the representative whose family income is related to. 
    representative = models.ForeignKey(Representative, related_name='family_income', blank=False, null=True,
        help_text=_('Family Income'))
    #: ID of Asset declaration document
    ad_id = models.IntegerField(default=0, blank=True, null=True, help_text=_('Asset Declaration Id'))
    #: submission date - asset declaration 
    submission_date = models.DateField(blank=True, null=True, help_text=_('Asset Declaration submission date'))
    #: html table containing the data related to family income
    html_table = models.TextField(blank=True, null=True, help_text=_('Family income details'))
'''

''' New model with each line in the HTML table as a row here'''


class FamilyIncome(models.Model):
    """A list of details regarding MP's family income"""
    #: ID of the representative whose family income is related to.
    representative = models.ForeignKey(Representative, related_name='family_income', blank=False, null=True,
                                       help_text=_('Family Income'))
    #: ID of Asset declaration document
    ad_id = models.IntegerField(default=0, blank=True, null=True, help_text=_('Asset Declaration Id'))
    #: submission date - asset declaration
    submission_date = models.DateField(blank=True, null=True, help_text=_('Asset Declaration submission date'))
    #: Names
    fam_name = models.TextField(blank=True, help_text=_('Name of family member'))
    #: role
    fam_role = models.TextField(blank=True, help_text=_('Role of family member'))
    #: Gender
    fam_gender = models.TextField(blank=True, help_text=_('Gender of family member'))
    #: age
    fam_date_of_birth = models.DateField(blank=True, null=True, help_text=_('Date of Birth'))
    #: Total income  = sum of paid work and entrepeneurial income in GEL and USD with dollars converted using 1.65
    # exchange rate
    fam_income = models.IntegerField(default=0, blank=True, null=True, help_text=_('Total Income of family member'))
    #: cars
    fam_cars = models.TextField(blank=True, help_text=_('Cars owned by family member'))


class Url(models.Model):
    """Urls belonging to a representative."""
    #: representative this url belongs to
    representative = models.ForeignKey(Representative,
                                       related_name='urls', null=True,
                                       help_text=_('Representative'))
    #: label of this url
    label = models.CharField(max_length=255, blank=False, default=_('Homepage'),
                             help_text=_('Label for this Url, e.g. Homepage, Facebook, Twitter, etc.'))
    #: the actual url; text field because georgian urls can become very long
    url = models.TextField(blank=False, help_text=_('The URL'))

    def __unicode__(self):
        return u'%s: %s - %s' % (str(self.representative.name), self.label, self.url)


ATTENDANCE_GROUP_CHOICES = (
    (0, _('very low')),
    (1, _('low')),
    (2, _('ordinary')),
    (3, _('high')),
    (4, _('very high')),
)


class Attendance(models.Model):
    """A representative's attendance record."""
    #: number of attended votes
    attended = models.IntegerField(default=0,
                                   help_text=_('Number of Attended Votes'))
    #: pre-calculated percentage of attended votes
    percentage_attended = models.IntegerField(default=0,
                                              help_text=_('Pre-calculated Percentage of Attended Votes'))
    #: number of absent votes
    absent = models.IntegerField(default=0,
                                 help_text=_('Number of Absent Votes'))
    #: pre-calculated percentage of absent votes
    percentage_absent = models.IntegerField(default=0,
                                            help_text=_('Pre-calculated Percentage of Absent Votes'))
    #: pre-calculated number of total votes
    total = models.IntegerField(default=0,
                                help_text=_('Number of Pre-calculated Total Votes'))
    #: attendance group
    group = models.IntegerField(default=0,
                                choices=ATTENDANCE_GROUP_CHOICES,
                                help_text=_('Voting Attendance in Relation to other Representatives'))
    #: representative this attendance record belongs to
    representative = models.ForeignKey(Representative,
                                       null=False, related_name='attendance',
                                       help_text=_('Representative'))

    def __unicode__(self):
        return u'%s: %s/%s' % (str(self.representative.name),
                               str(self.attended), str(self.total))


class RandomRepresentative(models.Model):
    """Defines the randomly selected representative of the day."""
    #: date when the current random representative was set
    date_set = models.DateTimeField(help_text=_('When random representative was set'))
    #: random representative
    representative = models.ForeignKey(Representative,
                                       null=True, help_text=_('Random Representative'))

    @classmethod
    def get(cls):
        """
        Gets current random representative or generates and returns new one if current one is older than 1 day
        @return: Random representative
        @rtype: class
        """
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        date_set = datetime.datetime(
            now.year, now.month, now.day, 0, 0).replace(tzinfo=utc)

        try:
            rr = RandomRepresentative.objects.all()[0]
            if (now - rr.date_set).days >= 1:
                rr.date_set = date_set
                try:
                    rr.representative = Representative.parliament.order_by('?')[0]
                    rr.save()
                except IndexError:
                    pass
        except IndexError:
            try:
                representative = Representative.parliament.order_by('?')[0]
            except IndexError:
                representative = None

            rr = RandomRepresentative(date_set=date_set,
                                      representative=representative)
            rr.save()

        return rr.representative

    def __unicode__(self):
        if self.representative:
            return u'%s' % self.representative.name
        else:
            return _('Unknown')
