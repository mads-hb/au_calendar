from credentials import USERNAME, PASSWORD
import ics
from mechanize import Browser
from bs4 import BeautifulSoup
from typing import Set
import re
import sys
from datetime import datetime
import locale
import pytz
from pprint import pprint


locale.setlocale(locale.LC_ALL, 'da_DK')
TZ = pytz.timezone("CET")


def parse(course, content) -> Set:
    """Parse html table"""
    soup = BeautifulSoup(content, "html.parser")
    elem = soup.strong
    activity = ""
    events = set()
    while elem != None:
        if re.match("<strong>.+</strong>", str(elem)) != None:
            activity = elem.text
        elif re.search("<table border=\"1\">", str(elem), re.MULTILINE) != None:
            for t in elem.find_all("tr"):
                # print(t.prettify(), "\n---------------------------\n")
                es = parse_table(t, course, activity)
                events.update(es)
        # Reset to find next element
        elem = elem.next_sibling
    return events


def make_event(course, activity, location, start, end, weekday, weeknum):
    d_str = "{}, WeekDay:{}, WeekNum{}, Y{}".format(
        start, weekday, weeknum, datetime.now().year)
    d = datetime.strptime(
        d_str, "%H, WeekDay:%A, WeekNum%W, Y%Y").replace(tzinfo=TZ)
    name = "{} ({})".format(course.title(), activity.lower())
    e = ics.Event(name=name, begin=d.replace(
        minute=15), end=d.replace(hour=int(end)), location=location)
    return e


def parse_table(table, course, activity) -> Set:
    weekday = table.find("td").next_sibling
    time = weekday.next_sibling
    (start, end) = time.text.replace(" ", "").split("-")
    location = time.next_sibling
    periods = location.next_sibling.text.replace("uge ", "").split(", ")
    events = set()
    for p in periods:
        if "-" not in p:
            e = make_event(course, activity, location.text,
                           start, end, weekday.text, p)
            continue
        (s, e) = p.split("-")
        for i in range(int(s), int(e) + 1):
            i = i - 1
            if len(str(i)) == 1:
                i = "0" + str(i)
            e = make_event(course, activity, location.text,
                           start, end, weekday.text, i)
            events.add(e)
    return events


def main():
    payload = {"ID": USERNAME, "password": PASSWORD}
    br = Browser()
    br.set_handle_robots(False)
    br.open(
        "https://timetable.scitech.au.dk/apps/skema/VaelgElevskema.asp?webnavn=skema")
    br.select_form(nr=0)
    br["ID"] = USERNAME
    br["password"] = PASSWORD
    r = br.submit()
    soup = BeautifulSoup(r.read(), "html.parser")
    courses = [c.text for c in soup.find_all("h3")]
    content = re.split("<h3>.+</h3>", str(soup.html))[1:]
    events = set()
    for (course, cont) in zip(courses, content):
        es = parse(course, cont)
        events.update(es)
    cal = ics.Calendar(events=events, creator="mads@baattrup.com")
    return cal


if __name__ == '__main__':
    cal = main()
    fname = "uni_calendar.ics"
    with open(fname, "w") as f:
        f.write(str(cal))
