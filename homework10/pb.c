#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <zlib.h>
#include "deviceapps.pb-c.h"

#define MAGIC  0xFFFFFFFF
#define DEVICE_APPS_TYPE 1

typedef struct pbheader_s {
    uint32_t magic;
    uint16_t type;
    uint16_t length;
} pbheader_t;
#define PBHEADER_INIT {MAGIC, 0, 0}

typedef struct apps_installed_s {
    char *dev_type;
    char *dev_id;
    double *lat;
    double *lon;
    uint32_t *apps;
    size_t n_apps;
} apps_installed_t;


int pack_and_write(apps_installed_t *ua, gzFile f) {
    DeviceApps msg = DEVICE_APPS__INIT;
    DeviceApps__Device device = DEVICE_APPS__DEVICE__INIT;
    void *buf = NULL;
    unsigned len;

    if (ua->dev_id) {
        device.has_id = 1;
        device.id.data = (uint8_t*)ua->dev_id;
        device.id.len = strlen(ua->dev_id);
    }

    if (ua->dev_type) {
        device.has_type = 1;
        device.type.data = (uint8_t*)ua->dev_type;
        device.type.len = strlen(ua->dev_type);
    }
    msg.device = &device;

    if (ua->lat) {
        msg.has_lat = 1;
        msg.lat = *ua->lat;
    }

    if (ua->lon) {
        msg.has_lon = 1;
        msg.lon = *ua->lon;
    }

    msg.n_apps = ua->n_apps;
    msg.apps = ua->apps;
    len = device_apps__get_packed_size(&msg);

    if ((buf = malloc(len)) == NULL) {
        PyErr_SetString(PyExc_MemoryError, "Can't allocate memory");
        return -1;
    }

    device_apps__pack(&msg, buf);

    pbheader_t header = PBHEADER_INIT;
    header.magic = MAGIC;
    header.type = DEVICE_APPS_TYPE;
    header.length = len;

    if ((gzwrite(f, &header, sizeof(header))) <= 0) {
        PyErr_SetString(PyExc_IOError, "Can't write header to file");
        free(buf);
        return -1;
    }

    if ((gzwrite(f, buf, len)) <= 0) {
        PyErr_SetString(PyExc_IOError, "Can't write message to file");
        free(buf);
        return -1;
    }

    free(buf);
    return len;
}


// Extract values from dict object to struct
apps_installed_t* serialize_dict(PyObject *item) {
    apps_installed_t *ua = calloc(1, sizeof(apps_installed_t));
    if (ua == NULL) {
        PyErr_SetString(PyExc_MemoryError, "Can't allocate memory");
        return NULL;
    }

    PyObject *device = PyDict_GetItemString(item, "device");
    if (device == NULL) {
        // Skip this item
        return NULL;
    }

    if (!PyDict_Check(device)) {
        PyErr_SetString(PyExc_TypeError, "'device' must be a dictionary");
        return NULL;
    }

    PyObject *dev_type = PyDict_GetItemString(device, "type");
    if (dev_type != NULL) {
        if (!PyString_Check(dev_type)) {
            PyErr_SetString(PyExc_TypeError, "'type' must be a string");
            return NULL;
        }
        ua->dev_type = PyString_AsString(dev_type);
    }

    PyObject *dev_id = PyDict_GetItemString(device, "id");
    if (dev_id != NULL) {
        if (!PyString_Check(dev_id)) {
            PyErr_SetString(PyExc_TypeError, "'id' must be a string");
            return NULL;
        }
        ua->dev_id = PyString_AsString(dev_id);
    }

    PyObject *lat = PyDict_GetItemString(item, "lat");
    if (lat != NULL) {
        if (!PyNumber_Check(lat)) {
            PyErr_SetString(PyExc_TypeError, "'lat' must be a double");
            return NULL;
        }
        ua->lat = malloc(sizeof(double));
        if (ua->lat == NULL) {
            PyErr_SetString(PyExc_MemoryError, "Can't allocate memory");
            return NULL;
        }
        *ua->lat = PyFloat_AS_DOUBLE(PyNumber_Float(lat));
    }

    PyObject *lon = PyDict_GetItemString(item, "lon");
    if (lon != NULL) {
        if (!PyNumber_Check(lat)) {
            PyErr_SetString(PyExc_TypeError, "'lon' must be a double");
            return NULL;
        }
        ua->lon = malloc(sizeof(double));
        if (ua->lon == NULL) {
            PyErr_SetString(PyExc_MemoryError, "Can't allocate memory");
            return NULL;
        }
        *ua->lon = PyFloat_AS_DOUBLE(PyNumber_Float(lon));
    }

    PyObject *apps = PyDict_GetItemString(item, "apps");
    if (apps != NULL) {
        if (!PySequence_Check(apps)) {
            PyErr_SetString(PyExc_TypeError, "'apps' must be a sequence");
            return NULL;
        }
        ua->n_apps = PySequence_Size(apps);
        ua->apps = malloc(ua->n_apps * sizeof(uint32_t));
        if (ua->apps == NULL) {
            PyErr_SetString(PyExc_MemoryError, "Can't allocate memory");
            return NULL;
        }
        apps = PyObject_GetIter(apps);
        int i = 0;
        PyObject *app;
        while ((app = PyIter_Next(apps))) {
            ua->apps[i++] = PyLong_AsLong(PyNumber_Long(app));
        }
    }

    return ua;
}


// Read iterator of Python dicts
// Pack them to DeviceApps protobuf and write to file with appropriate header
// Return number of written bytes as Python integer
static PyObject* py_deviceapps_xwrite_pb(PyObject* self, PyObject* args) {
    const char* path;
    PyObject* o;
    PyObject* item;

    if (!PyArg_ParseTuple(args, "Os", &o, &path))
        return NULL;

    o = PyObject_GetIter(o);
    if (!o)
        return NULL;

    gzFile f = gzopen(path, "wb");
    if (f == Z_NULL) {
        PyErr_SetString(PyExc_IOError, "Can't open file");
        Py_DECREF(o);
        return NULL;
    }

    int len = 0;
    int total_len = 0;
    apps_installed_t *ua;
    while ((item = PyIter_Next(o))) {
        if (!PyDict_Check(item)) {
            PyErr_SetString(PyExc_TypeError, "'item' must be a dictionary");
            return NULL;
        }

        if ((ua = serialize_dict(item)) != NULL) {
            if ((len = pack_and_write(ua, f)) == -1) {
                Py_DECREF(item);
                gzclose(f);
                return NULL;
            }
            total_len += len;
            free(ua->lat);
            free(ua->lon);
            free(ua->apps);
            free(ua);
        }
        Py_DECREF(item);
    }
    gzclose(f);
    Py_DECREF(o);

    printf("Write to: %s\n", path);
    return PyInt_FromLong(total_len);
}


// Unpack only messages with type == DEVICE_APPS_TYPE
// Return iterator of Python dicts
static PyObject* py_deviceapps_xread_pb(PyObject* self, PyObject* args) {
    const char* path;

    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;

    printf("Read from: %s\n", path);
    Py_RETURN_NONE;
}


static PyMethodDef PBMethods[] = {
     {"deviceapps_xwrite_pb", py_deviceapps_xwrite_pb, METH_VARARGS, "Write serialized protobuf to file fro iterator"},
     {"deviceapps_xread_pb", py_deviceapps_xread_pb, METH_VARARGS, "Deserialize protobuf from file, return iterator"},
     {NULL, NULL, 0, NULL}
};


PyMODINIT_FUNC initpb(void) {
     (void) Py_InitModule("pb", PBMethods);
}
