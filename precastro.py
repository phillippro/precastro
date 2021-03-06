# Copyright 2012-2015 Peter Williams
# Licensed under the GNU General Public License, version 3 or higher.

"""precastro - precision astronomy time and coordinate routines

"""

import _precastro
from pwkit.astutil import *

__all__ = ('PrecAstroError NovasError SofaError UnsupportedTimescaleError '
           'Time now CelestialObject SiderealObject objcols '
           'Observer EarthObserver').split ()

_oktimescales = frozenset ('TAI UTC UT1 TT TCG TCB TDB'.split ())
C_AUDAY = 173.1446326846693 # copied from novascon.c


class PrecAstroError (Exception):
    def __init__ (self, fmt, *args):
        if len (args):
            self.pamessage = fmt % args
        else:
            self.pamessage = str (fmt)

    def __str__ (self):
        return self.pamessage


class NovasError (PrecAstroError):
    def __init__ (self, func, code):
        self.func = func
        self.code = code

    def __str__ (self):
        return 'NOVAS error code #%d in function %s' % (self.code, self.func)


class SofaError (PrecAstroError):
    def __init__ (self, func, code):
        self.func = func
        self.code = code

    def __str__ (self):
        return 'SOFA error code #%d in function %s' % (self.code, self.func)


class UnsupportedTimescaleError (PrecAstroError):
    def __init__ (self, timescale):
        self.timescale = timescale

    def __str__ (self):
        return 'operation not supported with timescale ' + self.timescale


def _checktimescale (timescale):
    if timescale not in _oktimescales:
        raise ValueError ('illegal timescale name "%s"' % timescale)


def _checksofacode (func, code, dubiousok):
    if code == 1 and not dubiousok:
        raise SofaError (func, code)
    elif code:
        raise SofaError (func, code)


class Time (object):
    """A precisely-measured time and its associated timescale.

Times are stored in the IAU SOFA format: as two double-precision
floating point numbers specifying a Julian Date. Each time is also
associated with a named timescale, for which 'UTC' and 'TT' are
currently well-supported.

UTC does not have well-defined behavior regarding leapseconds. SOFA's
implementation is such that UTC times on days with leapseconds will
progress at a different rate than on other days. Any kind of precise
measurement, and any math with :class:`Time` objects, should avoid UTC
at all costs. The only way to safely interchange UTC times is in
broken-down calendar format, so that leapseconds can be expressed as
(e.g.) HH:MM:60.375.
"""

    jd1 = None
    """The first Julian Date component."""

    jd2 = None
    """The second Julian Date component."""

    timescale = None
    """The timescale in which this time is measured. 'UTC' and 'TT'
    are somewhat implemented; additional support for TAI, UT1, TCG,
    TCB, and TDB is possible but not yet exposed in the Python."""

    def fromnow (self):
        """Set the object to represent the current time according
to the computer clock. The associated timescale is UTC.

:returns: *self*

There (bizarrely) seems to be no way to get the current time that
avoids the leapsecond ambiguity inherent in the POSIX time system,
so this value has ~1-second precision on leapsecond days. Things
should be better on non-leapsecond days, though of course the
accuracy of the system clock is a limitation.

As of summer 2012 there was apparently interest in the Linux community
in adding a CLOCK_TAI clockid_t for ``clock_gettime`` that would make
this all so much easier. It is possible that using the tzdata
"right/UTC" timezone would get things right, but that just seems
impossible to test, and not worth doing unless I can be sure that it's
actually right. Another source references ``ntp_adjtime(3)`` as a
possibility for querying the leapsecond subsystem to get this right.
"""
        from time import time
        self.fromPOSIX (time ())
        return self


    def fromPOSIX (self, time):
        """Set the object to represent the given POSIX time. The
associated timescale is UTC.

:arg time: a POSIX/Unix time
:type time: convertable to :class:`float`
:returns: *self*

It really seems as if we just can't do anything about the leapsecond
ambiguity: the "TAI minus 10" standard is appealing but apparently not
honored. We only really need this function to implement
:meth:`fromnow`, so if I ever find a way to get the current time in a
way that's leapsecond-safe, then this becomes a lot less pressing.

Note while both UTC and POSIX time are problematic regarding
leapseconds, they are problematic in different and non-canceling ways.
"""
        self.jd1 = 2440587.5
        self.jd2 = float (time / 86400.)
        self.timescale = 'UTC'
        return self


    def fromJD (self, jd, timescale):
        """Set the object to represent the given Julian Date and
timescale.

:arg jd: a Julian date
:type jd: convertable to :class:`float`
:arg timescale: the timescale being used (see :class:`Time` docs)
:type timescale: :class:`str`
:returns: *self*

Storing a JD as a single float limits precision to about 20.1
microseconds, according to Kaplan, Bartlett, & Harris (2011, USNO-AA
Tech Note 2011-02).
"""
        _checktimescale (timescale)
        self.jd1 = float (jd)
        self.jd2 = 0.0
        self.timescale = timescale
        return self


    def fromMJD (self, mjd, timescale):
        """Set the object to represent the given modified Julian Date and
timescale.

:arg mjd: a modified Julian date
:type mjd: convertable to :class:`float`
:arg timescale: the timescale being used (see :class:`Time` docs)
:type timescale: :class:`str`
:returns: *self*

JD = MJD + 2400000.5. This will offer some precision gains over a
double-precision representation of an full, un-modified Julian Date, but
they're probably not too large. Maybe mentioned in Kaplan et al (2011)?
"""
        _checktimescale (timescale)
        self.jd1 = 2400000.5
        self.jd2 = mjd
        self.timescale = timescale
        return self


    def fromcalendar (self, year, month, day, hour, minute, second, timescale,
                      dubiousok=False):
        """Set the object to represent the given Gregorian calendar
date in the given timescale.

:arg year: the year
:type year: convertable to :class:`int`
:arg month: the month
:type month: convertable to :class:`int`, range 1 to 12
:arg day: the day
:type day: convertable to :class:`int`, range 1 to 31
:arg hour: the hour
:type hour: convertable to :class:`int`, range 0 to 23
:arg minute: the minute
:type minute: convertable to :class:`int`, range 0 to 59
:arg second: the second
:type second: convertable to :class:`float`, range 0 to 60.99999...
:arg timescale: the timescale being used (see :class:`Time` docs)
:type timescale: :class:`str`
:arg dubiousok: whether to accept extreme years
:type dubiousok: :class:`bool`
:returns: *self*
:raises: :exc:`SofaError` for bad inputs

Uses the Gregorian calendar system, which has the 100- and 400-year
leap day rules. SOFA docs say that the algorithm is valid to -4799
January 1 and uses the "proleptic Gregorian calendar" without paying
attention to, say, when the Gregorian calendar was actually adopted.

This is currently the only way to set a UTC date that can properly
account for leapseconds. But I know of no way to get the current
computer time in this broken-down format without going through POSIX
time, so that's not actually helpful.
"""
        _checktimescale (timescale)
        code, self.jd1, self.jd2 = _precastro.iauDtf2d (timescale.encode ('ascii'),
                                                        year, month, day,
                                                        hour, minute, second)
        _checksofacode ('dtf2d', code, dubiousok)
        self.timescale = timescale
        return self


    def fromfdcal (self, year, month, day, fday, timescale, dubiousok=False):
        """Set the object to represent the given Gregorian calendar
date, with a fractional day, in the given timescale.

:arg year: the year
:type year: convertable to :class:`int`
:arg month: the month
:type month: convertable to :class:`int`, range 1 to 12
:arg day: the day
:type day: convertable to :class:`int`, range 1 to 31
:arg fday: the day fraction
:type fday: convertable to :class:`float`, range 0.0 to 1.0
:arg timescale: the timescale being used (see :class:`Time` docs)
:type timescale: :class:`str`
:arg dubiousok: whether to accept extreme years
:type dubiousok: :class:`bool`
:returns: *self*
:raises: :exc:`SofaError` for bad inputs

Mirrored by :meth:`ascalendar`. The range of *fday* isn't actually
checked, and is just added to the JD resulting from a calendar
computation.

Uses the Gregorian calendar system, which has the 100- and 400-year
leap day rules. SOFA docs say that the algorithm is valid to -4799
January 1 and uses the "proleptic Gregorian calendar" without paying
attention to, say, when the Gregorian calendar was actually adopted.

This has the same bad leapsecond semantics as JD computations, so
UTC conversions will probably be subject to the usual pitfalls.
"""
        _checktimescale (timescale)
        code, self.jd1, self.jd2 = _precastro.iauDtf2d (timescale.encode ('ascii'),
                                                        year, month, day, 0, 0, 0)
        _checksofacode ('dtf2d', code, dubiousok)
        self.jd2 += fday
        self.timescale = timescale
        return self


    def fromjepoch (self, julian_epoch):
        """Set the object to represent the given Julian epoch.

:arg julian_epoch: a Julian epoch (eg 2005.37)
:type julian_epoch: convertable to :class:`float`
:returns: *self*

A Julian epoch measures years of exactly 365.25 days long in the TT
timescale.
"""
        self.jd1, self.jd2 = _precastro.iauEpj2jd (julian_epoch)
        self.timescale = 'TT'
        return self


    def asJD (self):
        """Return the time as a Julian Date.

:returns: the time as a Julian Date
:rtype: :class:`float`

The one-value representation limits precision to about 20
microseconds.
"""
        return self.jd1 + self.jd2


    def asMJD (self):
        """Return the time as a modified Julian Date.

:returns: the time as a modified Julian Date
:rtype: :class:`float`

The precision may be somewhat superior to that given by :meth:`asJD`,
but the difference will probably be minor.
"""
        return (self.jd1 - 2400000.5) + self.jd2


    def asTT (self, dubiousok=False):
        """Return a :class:`Time` object equivalent to this one, but
in the TT timescale.

:arg dubiousok: whether to accept extreme dates
:type dubiousok: :class:`bool`
:returns: an equivalent time in the TT timescale
:rtype: :class:`Time`
:raises: :exc:`SofaError` if extrapolating to an unacceptably extreme date
:raises: :exc:`UnsupportedTimescaleError` if there's no implementation
  to convert *self* to TT.

If the timescale of *self* is a TT, a copy is returned. Right now the
only other supported timescales are TAI and UTC. Other conversions can
be implemented as the need arises.
"""
        res = Time ()
        res.timescale = 'TT'

        if self.timescale == 'TT':
            res.jd1, res.jd2 = self.jd1, self.jd2
        elif self.timescale == 'TAI':
            code, res.jd1, res.jd2 = _precastro.iauTaitt (self.jd1, self.jd2)
            _checksofacode ('taitt', code, dubiousok)
        elif self.timescale == 'UTC':
            code, res.jd1, res.jd2 = _precastro.iauUtctai (self.jd1, self.jd2)
            _checksofacode ('utctai', code, dubiousok)
            code, res.jd1, res.jd2 = _precastro.iauTaitt (res.jd1, res.jd2)
            _checksofacode ('taitt', code, dubiousok)
        else:
            raise UnsupportedTimescaleError (self.timescale)

        return res


    def asTDB (self, ttok=False):
        """Return a :class:`Time` object equivalent to this one, but
in the TDB timescale.

:arg ttok: whether to accept TT as close enough (~2 ms differences)
:type ttok: :class:`bool`
:returns: an equivalent time in the TDB, or maybe TT, timescale
:rtype: :class:`Time`
:raises: :exc:`UnsupportedTimescaleError` if there's no implementation
  to convert *self* to TDB.

If the timescale of *self* is a TDB, a copy is returned. Right now,
the only other option is to return a TT time using :meth:`asTT`, if
*ttok* is :const:`True`. Note that in this case the returned time will
have its :attr:`timescale` equal to "TT", not to "TDB".
"""
        if self.timescale == 'TDB':
            res = Time ()
            res.timescale = 'TDB'
            res.jd1, res.jd2 = self.jd1, self.jd2
            return res

        if not ttok:
            raise UnsupportedTimescaleError (self.timescale)

        return self.asTT ()


    def asBJD (self, obj, ttok=True):
        """Return a :class:`Time` object adjusted to the solar system barycenter,
correcting for travel time to the :class:`SiderealObject` *obj*.

:arg obj: the reference object
:type obj: :class:`SiderealObject`
:arg ttok: whether TT rather than TDB as the ephemeris time is OK (~2 ms errors)
:type ttok: :class:`bool`
:returns: a time adjusted to the barycenter
:rtype: :class:`Time`

The output time will be in either TT or TDB timescale, depending on what we know
how to obtain from the timescale of *self*.

Our accuracy ought to be about 0.1 s. Here are some of the things we don't do
right that should affect our results. (Most of this list is from Jason Eastman's
documentation for the Ohio State University BJD calculator.)

* Roemer delay for solar system sources: <~ 100 s
  (this is negligible for things outside of the solar system)
* Observatory site rather than geocenter: 8-22 ms
* Proper conversion from TT to TDB: ~2 ms (according to Wikipedia)
* Einstein term: ~1 ms
* TT(BIPM) instead of TT(TAI): ~30 us
* Correct observatory elevation: ~10 us
* Shapiro delay: ~1 us
* Proper Earth Orientation Parameters: ~1 us
* Proper ITRF observatory site: ~30 ns
* Integrated rather than approximate TT-to-TDB conversion: ~20 ns
"""
        earth = EphemObject ('earth')
        tdb = self.asTDB (ttok=ttok)

        from math import cos, sin
        xhat = cos (obj.dec) * cos (obj.ra)
        yhat = cos (obj.dec) * sin (obj.ra)
        zhat = sin (obj.dec)

        # these are in AU:
        xobs, yobs, zobs = earth.ephem (tdb, ttok=ttok)[0]
        jdelta = (xobs * xhat + yobs * yhat + zobs * zhat) / C_AUDAY

        tdb.jd2 += jdelta
        return tdb


    def ascalendar (self):
        """Convert the time to Gregorian calendar format.

:returns: ``(year, month, day, fraction-of-day)``
:rtype: (:class:`int`, :class:`int`, :class:`int`, :class:`float`)
:raises: :exc:`SofaError` if using an unacceptably extreme date
"""
        res, yr, mo, dy, frac = _precastro.iauJd2cal (self.jd1, self.jd2)
        _checksofacode ('jd2cal', res, False)
        return yr, mo, dy, frac


    def fmtcalendar (self, precision=0, dubiousok=False):
        """Format the time as a calendar date/time.

:arg precision: how many decimal places of precision in the second
  component to use (default: 0, range: > -4)
:type precision: :class:`int`
:arg dubiousok: whether to accept extreme dates
:type dubiousok: :class:`bool`
:returns: the time formatted as a calendar date/time
:rtype: :class:`str`
:raises: :exc:`SofaError` if using an unacceptably extreme date

The returned string takes the form 'YYYY/MM/DD HH:MM:SS.SSSS', where
the number of decimal places used for the seconds varies. If *precision*
is less than one, the decimal point and fractional parts are omitted.
If precision is less than zero, the reported values are rounded as
appropriate but trailing zeros are still present in the string.
"""
        info = _precastro.iauD2dtf_tweak (self.timescale.encode ('ascii'),
                                          precision, self.jd1, self.jd2)
        _checksofacode ('d2dtf', info[0], dubiousok)
        ymdhmsf = list (info[1:])

        if precision < 1:
            ymdhmsf[6] = ''
        else:
            ymdhmsf[6] = '.%0*d' % (precision, ymdhmsf[6])

        return '%d/%02d/%02d %02d:%02d:%02d%s' % tuple (ymdhmsf)


def now ():
    """Get the current time.

:returns: the current time from the system clock
:rtype: :class:`Time`

Shorthand for ``Time().fromnow()``.
"""
    return Time ().fromnow ()


def _open_ephem ():
    """Note that this function must be called before computing NOVAS things even
    for non-ephemeris objects, because the internal computations need the Earth/Sun
    ephemerides to compute the observer's location. I discovered this by realizing
    that changing an object's parallax wasn't having any effect on astropos()."""

    from os.path import dirname, join
    p = join (dirname (_precastro.__file__), '_precastro-DEc421.dat')
    code, jd1, jd2, de_num = _precastro.ephem_open (p)
    if code:
        raise NovasError ('ephem_open', code)


class CelestialObject (object):
    """An object in space. This is an abstract
base class; see :class:`SiderealObject` and :class:`EphemObject`.
"""

    def __init__ (self):
        self._handle = _precastro.novas_object ()


    def horizonpos (self, time, earthobs, lowaccuracy=False, deltat=0.,
                    xp=0., yp=0., refract=False):
        """Compute the object's horizon coordinates at the specified time and
position on Earth.

:arg time: the time
:type time: :class:`Time`
:arg earthobs: the location on Earth
:type earthobs: :class:`EarthObserver`
:arg lowaccuracy: whether to perform a faster, but lower-accuracy calculation
:type lowaccuracy: optional :class:`bool`
:arg deltat: the difference TT - UT1 at *time* in seconds
:type deltat: optional :class:`float`
:arg xp: x coordinate of the celestial intermediate pole with respect to
  the ITRS reference pole in arcseconds.
:type xp: optional :class:`float`
:arg yp: y coordinate of the celestial intermediate pole with respect to
  the ITRS reference pole in arcseconds.
:type yp: optional :class:`float`
:arg refract: whether to apply refraction corrections (default :const:`False`)
:type refract: optional :class:`bool`
:returns: ``(azimuth, elevation)`` in radians
:rtype: :class:`tuple` of :class:`float`

*deltat*, *xp*, and *yp* all default to zero, which is fine in many cases.

If *refract* is :const:`True`, "standard" atmospheric conditions are assumed.
If it is set to the integer 2, the atmospheric conditions defined in the
*earthobs* object are used.
"""

        if not isinstance (earthobs, EarthObserver):
            raise ValueError ('must provide an observer position on Earth; '
                              'got "%s"' % earthobs)

        # Based on the docs, topocentric position is what we want.
        _open_ephem ()
        ra, dec = self.topopos (time, earthobs, deltat=deltat,
                                lowaccuracy=lowaccuracy)
        ra *= R2H # oh well, roundtrip the conversions
        dec *= R2D

        ut1 = time.asTT ().asJD () - deltat

        zd, az, rar, decr = _precastro.equ2hor (ut1, deltat, int (lowaccuracy),
                                                xp, yp,
                                                earthobs._handle.on_surf,
                                                ra, dec, int(refract))
        # rar and decr are (potentially) refracted topocentric RA and dec.
        # We ignore them.
        return az * D2R, (90. - zd) * D2R


class SiderealObject (CelestialObject):
    """A sidereal celestial object.
"""

    def __init__ (self, ra=None, dec=None):
        super (SiderealObject, self).__init__ ()

        ret = _precastro.make_cat_entry ('', '', 0, 0., 0., 0., 0.,
                                         0., 0., self._handle.star)
        if ret:
            raise NovasError ('make_cat_entry', ret)

        ret = _precastro.make_object (2, 0, ' ', self._handle.star, self._handle)
        if ret:
            raise NovasError ('make_object', ret)

        if ra is not None:
            if isinstance (ra, basestring):
                self.ra = parsehours (ra)
            else:
                self.ra = ra

        if dec is not None:
            if isinstance (dec, basestring):
                self.dec = parsedeglat (dec)
            else:
                self.dec = dec

        self.promoepoch = 2451545.0 # J2000 epoch; unpatched NOVAS's assumption


    def _get_ra (self):
        return self._handle.star.ra * H2R

    def _set_ra (self, rarad):
        self._handle.star.ra = rarad * R2H

    ra = property (_get_ra, _set_ra, doc='object\'s ICRS J2000 right ascension in radians')

    def _get_dec (self):
        return self._handle.star.dec * D2R

    def _set_dec (self, decrad):
        self._handle.star.dec = decrad * R2D

    dec = property (_get_dec, _set_dec, doc='object\'s ICRS J2000 declination in radians')

    def setradec (self, rarad, decrad):
        """Set the object's :attr:`ra` and :attr:`dec`

:arg rarad: right ascension in radians
:type rarad: :class:`float`
:arg decrad: declination in radians
:type decrad: :class:`float`
:returns: *self*

This is a convenience function, completely equivalent to setting :attr:`ra` and
:attr:`dec` in two statements.
"""
        self.ra = rarad
        self.dec = decrad
        return self


    def parseradec (self, rastr, decstr):
        """Set the object's :attr:`ra` and :attr:`dec` from a textual representation

:arg rastr: sexagesimal representation of the RA in hours
:type rastr: :class:`str`
:arg decstr: sexagesimal representation of the declination in degrees
:type decstr: :class:`str`
:returns: *self*
"""
        self.ra = parsehours (rastr)
        self.dec = parsedeglat (decstr)
        return self


    def fmtradec (self, **kwargs):
        """Return a textual representation of the object's :attr:`ra` and :attr:`dec`.

:arg kwargs: extra arguments to pass to :meth:`astutil.fmtradec`
:returns: the textualization
:rtype: :class:`str`
"""
        return fmtradec (self.ra, self.dec, **kwargs)


    def _get_promora (self):
        return self._handle.star.promora

    def _set_promora (self, promora_masperyr):
        self._handle.star.promora = promora_masperyr

    promora = property (_get_promora, _set_promora,
                        doc='''object\'s ICRS RA proper motion in mas per year

This is an offset, so ``ra(t) = ra + promora/cos(dec) * (t - promoepoch)``.
''')

    def _get_promodec (self):
        return self._handle.star.promodec

    def _set_promodec (self, promodec_masperyr):
        self._handle.star.promodec = promodec_masperyr

    promodec = property (_get_promodec, _set_promodec,
                        doc='object\'s ICRS declination proper motion in mas per year')

    def setpromo (self, promora_masperyr, promodec_masperyr):
        """Set the object's :attr:`promora` and :attr:`promodec`

:arg promora_masperyr: proper motion in right ascension, in milliarcseconds per year
:type promora_masperyr: :class:`float`
:arg promodec_masperyr: proper motion in declination, in milliarcseconds per year
:type promodec_masperyr: :class:`float`
:returns: *self*

This is a convenience function, completely equivalent to setting :attr:`promora` and
:attr:`promodec` in two statements.
"""
        self.promora = promora_masperyr
        self.promodec = promodec_masperyr
        return self


    def _get_parallax (self):
        return self._handle.star.parallax

    def _set_parallax (self, parallax_mas):
        self._handle.star.parallax = parallax_mas

    parallax = property (_get_parallax, _set_parallax,
                         doc='object\'s parallax in milliarcseconds')


    def _get_vradial (self):
        return self._handle.star.radialvelocity

    def _set_vradial (self, vradial_kmpers):
        self._handle.star.radialvelocity = vradial_kmpers

    vradial = property (_get_vradial, _set_vradial,
                        doc='object\'s radial velocity in km per second')


    def _get_promoepoch (self):
        return self._handle.star.promoepoch

    def _set_promoepoch (self, promoepoch_jdtdb):
        self._handle.star.promoepoch = promoepoch_jdtdb

    promoepoch = property (_get_promoepoch, _set_promoepoch,
                           doc='TDB JD for which effect of proper motion is zero; default is J2000')


    def setpecal (self, year, month, day, hour=0, minute=0, second=0,
                  timescale='UTC', **kwargs):
        """Set the proper-motion epoch to a calendar date.

:arg year: the year
:type year: :class:`int`
:arg month: the month
:type month: :class:`int`
:arg day: the day
:type day: :class:`int`
:arg hour: the hour (defaults to 0)
:type hour: :class:`int`
:arg minute: the minute (defaults to 0)
:type minute: :class:`int`
:arg second: the second (defaults to 0)
:type second: :class:`float`
:arg timescale: the timescale to use (defaults to 'UTC')
:type timescale: :class:`str`
:arg kwargs: extra keywords to pass to :meth:`Time.fromcalendar`
:returns: *self*

Set the "proper-motion epoch" to the given date. Because the date does not
often need to be precise, *hour*, *minute*, and *second* default to zero
for convenience, and likewise *timescale* defaults to "UTC".

The epoch thus generated is converted to the TT timescale, while the
timescale used for proper-motion calculations by NOVAS is TDB. My
understanding is that the difference between these is almost always
insignificant. If this becomes a problem, we can add a flag to override
this behavior, or you can set :attr:`SiderealObject.promoepoch` manually.
"""
        self.promoepoch = Time ().fromcalendar (year, month, day, hour, minute,
                                                second, timescale,
                                                **kwargs).asTT ().asJD ()
        return self


    def fromsesame (self, ident):
        """Fill in object information from the SIMBAD/Sesame database

:arg ident: the object name
:type ident: :class:`str`
:returns: *self*
:raises: :exc:`PrecAstroError` if the lookup seems to have failed

Looks up the object in SIMBAD or NED using the online service provided
by the CDS. To be explicit, this function performs an HTTP
request. This function will fill in :attr:`ra`, :attr:`dec`,
:attr:`promora`, :attr:`promodec`, :attr:`parallax`, and
:attr:`vradial`, if they're provided.

Note that SIMBAD can be inconsistent about proper motion settings. For
some sources, :attr:`ra` and :attr:`dec` are tweaked such that the
:attr:`promoepoch` is J2000. For others, this correction is not performed,
and you must separately discover and set :attr:`promoepoch` in order to
track proper motion correctly.
"""
        from urllib2 import urlopen
        from urllib import quote

        url = 'http://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame?' + quote (ident)

        for line in urlopen (url):
            if line.startswith ('#!'):
                raise PrecAstroError ('Simbad/Sesame lookup failed: ' + line[3:].strip ())

            a = line.strip ().split ()
            if not len (a):
                continue

            # The units for our fields are coincidentally the same as
            # those used by Simbad, for the most part ...

            if a[0] == '%J':
                self.ra = float (a[1]) * D2R
                self.dec = float (a[2]) * D2R
            elif a[0] == '%P':
                self.promora = float (a[1])
                self.promodec = float (a[2])
            elif a[0] == '%X':
                self.parallax = float (a[1])
            elif a[0] == '%V':
                self.vradial = float (a[2])

        return self


    def describe (self):
        '''Return a human-friendly string describing the object's properties

:returns: a multiline string describing the object's properites
:rtype: :class:`str`
'''
        s = ['ICRS J2000: ' + self.fmtradec ()]
        s.append ('Proper motion: %+.2f %+.2f mas/yr' % (self.promora, self.promodec))
        s.append ('Parallax: %.2f mas' % self.parallax)
        s.append ('Radial velocity: %+.2f km/s' % self.vradial)
        s.append ('Proper-motion epoch: %s [TDB]' %
                  Time ().fromJD (self.promoepoch, 'TDB').fmtcalendar ())
        return '\n'.join (s)


    def astropos (self, jd_tt, lowaccuracy=False):
        """Compute the source's "astrometric" place (defined below)

:arg jd_tt: the TT JD at which to evaluate the source's place
:type jd_tt: :class:`float` or :class:`Time`
:arg lowaccuracy: whether to perform a faster, but lower-accuracy calculation
:type lowaccuracy: optional :class:`bool`
:returns: tuple of ``(ra, dec)`` in radians
:rtype: ``(float, float)``
:raises: :exc:`NovasError` if the library routine fails
:raises: other exceptions if *jd_tt* cannot be converted to TT.

The *astrometric* place of a source is its location taking into
account parallax and proper motion for a geocentric observer with mean
equator and equinox of J2000.0. (Gravitational light bending,
aberration, and atmospheric refraction are not accounted for: that
would be its *virtual* place. If coordinates were additionally
expressed relative to the true epoch and equinox of date, that would
be its *apparent* place.)

The argument is treated as a :class:`float` JD, unless it is an
instance of :class:`Time`, in which case it is converted by calling
``jt_tt.asTT().asJD()``.
"""
        if isinstance (jd_tt, Time):
            jd_tt = jd_tt.asTT ().asJD ()

        _open_ephem ()
        code, ra, dec = _precastro.astro_star (jd_tt, self._handle.star, int (lowaccuracy))
        if code:
            raise NovasError ('astro_star', code)

        return ra * H2R, dec * D2R


    def topopos (self, jd_tt, earthobs, deltat=0., lowaccuracy=False):
        """Compute the source's "topocentric" place (defined below)

:arg jd_tt: the TT JD at which to evaluate the source's place
:type jd_tt: :class:`float` or :class:`Time`
:arg earthobs: the (earthbound) location at which to evaluate the place
:type earthobs: :class:`EarthObserver`
:arg deltat: the difference TT - UT1 at *time* in seconds (default: 0)
:type deltat: optional :class:`float`
:arg lowaccuracy: whether to perform a faster, but lower-accuracy calculation
:type lowaccuracy: optional :class:`bool`
:returns: tuple of ``(ra, dec)`` in radians
:rtype: ``(float, float)``
:raises: :exc:`NovasError` if the library routine fails
:raises: other exceptions if *jd_tt* cannot be converted to TT.

The *topocentric* place of a source is its location taking into account
parallax, proper motion, gravitational light bending, and aberration, for an
observer on the surface of the Earth, with respect to the true equator and
equinox of date. (Refraction is not accounted for. If the intended observer
were geocentric, that would be its *apparent* place. If the coordinates were
additionally expressed relative to a mean equator and equinox of J2000.0, that
would be its *virtual* place.)

The argument *time* is treated as a :class:`float` JD, unless it is an
instance of :class:`Time`, in which case it is converted by calling
``jt_tt.asTT().asJD()``.

The default of *deltat* is zero, which is fine for many applications.
"""
        if not isinstance (earthobs, EarthObserver):
            raise ValueError ('must provide an observer position on Earth; '
                              'got "%s"' % earthobs)

        if isinstance (jd_tt, Time):
            jd_tt = jd_tt.asTT ().asJD ()

        _open_ephem ()
        code, ra, dec = _precastro.topo_star (jd_tt, deltat,
                                              self._handle.star,
                                              earthobs._handle.on_surf,
                                              int (lowaccuracy))
        if code:
            raise NovasError ('topo_star', code)

        return ra * H2R, dec * D2R


# for combination with srctable:
objcols = 'ra dec promora promodec promoepoch parallax vradial'.split ()


_ephemnums = {
    'mercury': 1,
    'venus': 2,
    'earth': 3,
    'mars': 4,
    'jupiter': 5,
    'saturn': 6,
    'uranus': 7,
    'neptune': 8,
    'pluto': 9,
    'sun': 10,
    'moon': 11,
    }

class EphemObject (CelestialObject):
    """A celestial object with a position computed from an ephemeris."""

    def __init__ (self, name):
        super (EphemObject, self).__init__ ()

        if name not in _ephemnums:
            raise ValueError ('unrecognized ephemeris object name "%s"' % name)

        num = _ephemnums[name]

        # star info will be zero'ed out in this mode.
        ret = _precastro.make_object (0, num, ' ', None, self._handle)
        if ret:
            raise NovasError ('make_object', ret)


    def describe (self):
        '''Return a human-friendly string describing the object's properties

:returns: a multiline string describing the object's properites
:rtype: :class:`str`
'''
        for name, num in _ephemnums.iteritems ():
            if num == self._handle.number:
                break
        else:
            name = 'unknown?'

        return 'Ephemeris object "%s"' % name


    def ephem (self, time, ttok=True):
        """Return the object's position in phase space at the specified time.

:arg time: a time
:type time: :class:`Time`
:arg ttok: whether a time in the TT timescale is good enough (default: :const:`True`)
:type ttok: :class:`bool`
:returns: ``[[x, y, z], [vx, vy, vz]]``
:rtype: :class:`numpy.ndarray` of shape ``(2, 3)``
:raises: :exc:`NovasError` if there's a problem with the instance of the
  ephemeris.

*time* needs to be converted to TDB. The return values are measured in AU
and AU/day relative to the barycenter of the solarsystem, referenced to the
ICRS.
"""
        tdb = time.asTDB (ttok=ttok)
        _open_ephem ()
        ret, x, y, z, vx, vy, vz = _precastro.ephemeris_tweak (tdb.jd1, tdb.jd2,
                                                               self._handle, 0, 0)
        if ret:
            raise NovasError ('ephemeris')

        return np.asarray ([(x, y, z), (vx, vy, vz)])


    def astropos (self, jd_tt, lowaccuracy=False):
        """Compute the source's "astrometric" place (defined below)

:arg jd_tt: the TT JD at which to evaluate the source's place
:type jd_tt: :class:`float` or :class:`Time`
:arg lowaccuracy: whether to perform a faster, but lower-accuracy calculation
:type lowaccuracy: optional :class:`bool`
:returns: tuple of ``(ra, dec)`` in radians
:rtype: ``(float, float)``
:raises: :exc:`NovasError` if the library routine fails
:raises: other exceptions if *jd_tt* cannot be converted to TT.

The *astrometric* place of a source is its location taking into
account parallax and proper motion for a geocentric observer with mean
equator and equinox of J2000.0. (Gravitational light bending,
aberration, and atmospheric refraction are not accounted for: that
would be its *virtual* place. If coordinates were additionally
expressed relative to the true epoch and equinox of date, that would
be its *apparent* place.)

The argument is treated as a :class:`float` JD, unless it is an
instance of :class:`Time`, in which case it is converted by calling
``jt_tt.asTT().asJD()``.
"""
        if isinstance (jd_tt, Time):
            jd_tt = jd_tt.asTT ().asJD ()

        # distance is in AU. We ignore it.

        _open_ephem ()
        code, ra, dec, dist = _precastro.astro_planet (jd_tt,
                                                       self._handle,
                                                       int (lowaccuracy))
        if code:
            raise NovasError ('astro_planet', code)

        return ra * H2R, dec * D2R


    def topopos (self, jd_tt, earthobs, deltat=0., lowaccuracy=False):
        """Compute the source's "topocentric" place (defined below)

:arg jd_tt: the TT JD at which to evaluate the source's place
:type jd_tt: :class:`float` or :class:`Time`
:arg earthobs: the (earthbound) location at which to evaluate the place
:type earthobs: :class:`EarthObserver`
:arg deltat: the difference TT - UT1 at *time* in seconds (default: 0)
:type deltat: optional :class:`float`
:arg lowaccuracy: whether to perform a faster, but lower-accuracy calculation
:type lowaccuracy: optional :class:`bool`
:returns: tuple of ``(ra, dec)`` in radians
:rtype: ``(float, float)``
:raises: :exc:`NovasError` if the library routine fails
:raises: other exceptions if *jd_tt* cannot be converted to TT.

The *topocentric* place of a source is its location taking into account
parallax, proper motion, gravitational light bending, and aberration, for an
observer on the surface of the Earth, with respect to the true equator and
equinox of date. (Refraction is not accounted for. If the intended observer
were geocentric, that would be its *apparent* place. If the coordinates were
additionally expressed relative to a mean equator and equinox of J2000.0, that
would be its *virtual* place.)

The argument *time* is treated as a :class:`float` JD, unless it is an
instance of :class:`Time`, in which case it is converted by calling
``jt_tt.asTT().asJD()``.

The default of *deltat* is zero, which is fine for many applications.
"""
        if not isinstance (earthobs, EarthObserver):
            raise ValueError ('must provide an observer position on Earth; '
                              'got "%s"' % earthobs)

        if isinstance (jd_tt, Time):
            jd_tt = jd_tt.asTT ().asJD ()

        # distance is in AU. We ignore it.

        _open_ephem ()
        code, ra, dec, dist = _precastro.topo_planet (jd_tt, self._handle,
                                                      deltat,
                                                      earthobs._handle.on_surf,
                                                      int (lowaccuracy))
        if code:
            raise NovasError ('topo_planet', code)

        return ra * H2R, dec * D2R


class Observer (object):
    """An observer located on the Earth or in space. This is an abstract
base class; see :class:`EarthObserver`.
"""

    def __init__ (self):
        self._handle = _precastro.novas_observer ()


class EarthObserver (Observer):
    """An earthbound observer. FIXME: there are some ambiguities in the
NOVAS documentation about whether we're using WGS84, ITRF, or what,
although the differences are very, very small.
"""

    def __init__ (self):
        super (EarthObserver, self).__init__ ()
        _precastro.make_observer_at_geocenter (self._handle)


    def _get_latitude (self):
        return self._handle.on_surf.latitude * D2R

    def _set_latitude (self, latrad):
        self._handle.on_surf.latitude = latrad * R2D

    latitude = property (_get_latitude, _set_latitude,
                         doc='observer\'s geodetic WGS84 latitude in radians')


    def _get_longitude (self):
        return self._handle.on_surf.longitude * D2R

    def _set_longitude (self, lonrad):
        self._handle.on_surf.longitude = lonrad * R2D

    longitude = property (_get_longitude, _set_longitude,
                          doc='observer\'s east-positive geodetic WGS84 longitude in radians')


    def _get_height (self):
        return self._handle.on_surf.height

    def _set_height (self, heightmeters):
        self._handle.on_surf.height = heightmeters

    height = property (_get_height, _set_height,
                       doc='observer\'s WGS84 height in meters')


    def fmtlatlon (self, intersep=' ', **kwargs):
        """Return a textual representation of the objects :attr:`latitude`
and :attr:`longitude`.

:arg intersep: a string to place between the latitude and longitude strings
:type intersep: :class:`str`
:arg kwargs: extra arguments to pass to :meth:`astutil.fmtdeglat` and :meth:`astutil.fmtdeglon`
:returns: the textualization
:rtype: :class:`str`
"""
        return (fmtdeglat (self.latitude, **kwargs) + intersep +
                fmtdeglon (self.longitude, **kwargs))


    def parselatlon (self, latstr, lonstr):
        """Set the observer's :attr:`latitude` and :attr:`longitude` from
a textual representation.

:arg latstr: sexagesimal representation of the latitude in degrees
:type latstr: :class:`str`
:arg lonstr: sexagesimal representation of the longitude in degrees
:type lonstr: :class:`str`
:returns: *self*
"""
        self.latitude = parsedeglat (latstr)
        self.longitude = parsedeglon (lonstr)
        return self

    # TODO: temperature, pressure
