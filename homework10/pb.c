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


// https://github.com/protobuf-c/protobuf-c/wiki/Examples
void example() {
    DeviceApps msg = DEVICE_APPS__INIT;
    DeviceApps__Device device = DEVICE_APPS__DEVICE__INIT;
    void *buf;
    unsigned len;

    char *device_id = "e7e1a50c0ec2747ca56cd9e1558c0d7c";
    char *device_type = "idfa";
    device.has_id = 1;
    device.id.data = (uint8_t*)device_id;
    device.id.len = strlen(device_id);
    device.has_type = 1;
    device.type.data = (uint8_t*)device_type;
    device.type.len = strlen(device_type);
    msg.device = &device;

    msg.has_lat = 1;
    msg.lat = 67.7835424444;
    msg.has_lon = 1;
    msg.lon = -22.8044005471;

    msg.n_apps = 3;
    msg.apps = malloc(sizeof(uint32_t) * msg.n_apps);
    msg.apps[0] = 42;
    msg.apps[1] = 43;
    msg.apps[2] = 44;
    len = device_apps__get_packed_size(&msg);

    buf = malloc(len);
    device_apps__pack(&msg, buf);

    fprintf(stderr,"Writing %d serialized bytes\n",len); // See the length of message
    fwrite(buf, len, 1, stdout); // Write to stdout to allow direct command line piping

    free(msg.apps);
    free(buf);
}


int contains(PyObject *o, const char *s) {
    PyObject *key = PyString_FromString(s);
    if (PyDict_Contains(o, key)) {
        Py_DECREF(key);
        return 1;
    }
    Py_DECREF(key);
    return 0;
}


unsigned create_msg_and_write(char *device_id, char *device_type, double lat, double lon, uint32_t *apps, int n_apps, gzFile f) {
    DeviceApps msg = DEVICE_APPS__INIT;
    DeviceApps__Device device = DEVICE_APPS__DEVICE__INIT;
    void *buf;
    unsigned len;

    if (device_id) {
        device.has_id = 1;
        device.id.data = (uint8_t*)device_id;
        device.id.len = strlen(device_id);
    }

    if (device_type) {
        device.has_type = 1;
        device.type.data = (uint8_t*)device_type;
        device.type.len = strlen(device_type);
    }
    msg.device = &device;

    if (lat) {
        msg.has_lat = 1;
        msg.lat = lat;
    }

    if (lon) {
        msg.has_lon = 1;
        msg.lon = lon;
    }

    msg.n_apps = n_apps;
    msg.apps = apps;
    len = device_apps__get_packed_size(&msg);

    buf = malloc(len);
    device_apps__pack(&msg, buf);

    pbheader_t header = PBHEADER_INIT;
    header.magic = MAGIC;
    header.type = DEVICE_APPS_TYPE;
    header.length = len;

    gzwrite(f, &header, sizeof(header));
    gzwrite(f, buf, len);

    free(msg.apps);
    free(buf);
    return len;
}


// Extract values from dict
unsigned handle_item(PyObject *item, gzFile f) {
    char *device_type = NULL;
    char *device_id = NULL;
    if (contains(item, "device")) {
        PyObject *device = PyDict_GetItemString(item, "device");
        if (contains(device, "type")) {
            PyObject *type = PyDict_GetItemString(device, "type");
            device_type = PyString_AsString(type);
            Py_DECREF(type);
        }

        if (contains(device, "id")) {
            PyObject *id = PyDict_GetItemString(device, "id");
            device_id = PyString_AsString(id);
            Py_DECREF(id);
        }

        //Py_DECREF(device);
    }

    double latitude = 0, longitude = 0;
    if (contains(item, "lat")) {
        PyObject *lat = PyDict_GetItemString(item, "lat");
        latitude = PyFloat_AS_DOUBLE(PyNumber_Float(lat));
        Py_DECREF(lat);
    }

    if (contains(item, "lon")) {
        PyObject *lon = PyDict_GetItemString(item, "lon");
        longitude = PyFloat_AS_DOUBLE(PyNumber_Float(lon));
        Py_DECREF(lon);
    }

    uint32_t *applications = NULL;
    int n_apps = 0;
    if (contains(item, "apps")) {
        PyObject *apps = PyDict_GetItemString(item, "apps");
        n_apps = PySequence_Size(apps);
        applications = malloc(sizeof(uint32_t) * n_apps);
        PyObject *app;
        apps = PyObject_GetIter(apps);
        int i = 0;
        while ((app = PyIter_Next(apps))) {
            long appId = PyLong_AsLong(PyNumber_Long(app));
            applications[i++] = appId;
        }
        Py_DECREF(apps);
    }

    return create_msg_and_write(
        device_id,
        device_type,
        latitude,
        longitude,
        applications,
        n_apps,
        f
    );
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
    
    gzFile fi = gzopen(path, "wb");
    unsigned len = 0;
    while ((item = PyIter_Next(o))) {
        len += handle_item(item, fi);
        Py_DECREF(item);
    }
    gzclose(fi);
    
    Py_DECREF(o);
    
    printf("Write to: %s\n", path);
    return PyInt_FromLong(len);
    //Py_RETURN_NONE;
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
