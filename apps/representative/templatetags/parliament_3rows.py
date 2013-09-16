from django import template
from apps.representative.models import *

register = template.Library()

def _get_members():
  unit = Unit.objects.get(short="parliament")
  members = unit.active_term.representatives.all()
  members = Representative.by_lastname_firstname_first(members)
  for member in members:
      """
      Avoid a browser bug with names longer than available width making
      member boxes in the unit of the find page jump up a few pixels.
      You probably need to apply the template tag filter 'linebreaksbr' when
      using this.
      Note the replacement only done once - the box starts jumping again
      if there are three parts seperated by the linebreak *sigh*
      """
      member['name'] = member['firstname_first'].replace(' ', '\n', 1)
  return members

@register.inclusion_tag('representative/parl_row_li.html')
def get_mprow_of3(row_num):
    result = []
    allmps = _get_members()
    for i in range(row_num,len(allmps),3):
        result.append(allmps[i])
    return {'members': result}

