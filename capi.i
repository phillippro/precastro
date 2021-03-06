/* Copyright 2012 Peter Williams
 * Licensed under the GNU General Public License version 3 or higher. */

%module precastro
%include "typemaps.i"

%{
#include "novas.h"
#include "eph_manager.h"
#include "sofa.h"
%}


/* NOVAS */

%rename (novas_cat_entry) cat_entry;

typedef struct {
    char starname[SIZE_OF_OBJ_NAME];
    char catalog[SIZE_OF_CAT_NAME];
    long int starnumber;
    double ra;
    double dec;
    double promora;
    double promodec;
    double parallax;
    double radialvelocity;
    double promoepoch;
} cat_entry;

%rename (novas_object) object;

typedef struct {
    short int type;
    short int number;
    char name[SIZE_OF_OBJ_NAME];
    cat_entry star;
} object;

%rename (novas_on_surface) on_surface;

typedef struct {
    double latitude;
    double longitude;
    double height;
    double temperature;
    double pressure;
} on_surface;

%rename (novas_in_space) in_space;

typedef struct {
    double sc_pos[3];
    double sc_vel[3];
} in_space;

%rename (novas_observer) observer;

typedef struct {
    short int where;
    on_surface on_surf;
    in_space near_earth;
} observer;

short int astro_star (double jd_tt, cat_entry *star, short int accuracy,
		      double *OUTPUT, double *OUTPUT);

short int astro_planet (double jd_tt, object *ss_body, short int accuracy,
			double *OUTPUT, double *OUTPUT, double *OUTPUT);

short int topo_star (double jd_tt, double delta_t, cat_entry *star,
		       on_surface *position, short int accuracy,
		       double *OUTPUT, double *OUTPUT);

/* note that call signature differs from topo_star nontrivially! */
short int topo_planet (double jd_tt, object *ss_body, double delta_t,
		       on_surface *position, short int accuracy,
		       double *OUTPUT, double *OUTPUT, double *OUTPUT);

short int make_cat_entry (char star_name[SIZE_OF_OBJ_NAME],
			  char catalog[SIZE_OF_CAT_NAME],
			  long int star_num, double ra, double dec,
			  double pm_ra, double pm_dec, double parallax,
			  double rad_vel, cat_entry *star);

short int make_object (short int type, short int number, char name[51],
		       cat_entry *star_data, object *cel_obj);

short int ephem_open (char *ephem_name, double *OUTPUT, double *OUTPUT,
		      short int *OUTPUT);

short int ephem_close (void);

%apply double *OUTPUT { double *x, double *y, double *z,
                        double *vx, double *vy, double *vz };

%inline %{
    short int ephemeris_tweak (double jd1, double jd2, object *cel_obj, short int origin,
			       short int accuracy, double *x, double *y, double *z,
			       double *vx, double *vy, double *vz)
    {
	short int retval;
	double jd[2], pos[3], vel[3];
	jd[0] = jd1;
	jd[1] = jd2;
	retval = ephemeris (jd, cel_obj, origin, accuracy, pos, vel);
	*x = pos[0];
	*y = pos[1];
	*z = pos[2];
	*vx = vel[0];
	*vy = vel[1];
	*vz = vel[2];
	return retval;
    }
%}

void make_observer_at_geocenter (observer *obs_at_geocenter);

void equ2hor (double jd_ut1, double delta_t, short int accuracy,
	      double xp, double yp, on_surface *location, double ra,
	      double dec, short int ref_option,
	      double *OUTPUT, double *OUTPUT, double *OUTPUT, double *OUTPUT);

/* SOFA */

%apply int *OUTPUT { int *iy, int *im, int *id, int *h, int *m, int *s, int *f };

%inline %{
    int iauD2dtf_tweak (const char *scale, int ndp, double d1, double d2,
			int *iy, int *im, int *id, int *h, int *m,
			int *s, int *f)
    {
	int ihmsf[4], retval;
	retval = iauD2dtf (scale, ndp, d1, d2, iy, im, id, ihmsf);
	*h = ihmsf[0];
	*m = ihmsf[1];
	*s = ihmsf[2];
	*f = ihmsf[3];
	return retval;
    }
%}

int iauDtf2d (const char *scale, int iy, int im, int id, int ihr, int imn,
	      double sec, double *OUTPUT, double *OUTPUT);

int iauTaiutc (double tai1, double tai2, double *OUTPUT, double *OUTPUT);

int iauUtctai (double utc1, double utc2, double *OUTPUT, double *OUTPUT);

int iauTaitt (double tai1, double tai2, double *OUTPUT, double *OUTPUT);

void iauEpj2jd (double epj, double *OUTPUT, double *OUTPUT);

int iauJd2cal (double dj1, double dj2, int *OUTPUT, int *OUTPUT,
	       int *OUTPUT, double *OUTPUT);
