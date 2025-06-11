#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <math.h>
#include <object.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static PyObject *count_ngrams(PyObject *self, PyObject *args)
{
    const char *data;
    Py_ssize_t data_len;
    int length;
    if (!PyArg_ParseTuple(args, "y#i", &data, &data_len, &length))
    {
        goto err;
    }

    PyObject *counts = PyDict_New();
    if (!counts)
    {
        goto err;
    }

    for (size_t i = 0; i < data_len - length; i += 1)
    {
        PyObject *ngram = PyBytes_FromStringAndSize(data + i, length);
        if (!ngram)
        {
            goto err;
        }

        PyObject *item = PyDict_GetItem(counts, ngram);
        long value = item ? PyLong_AsLong(item) : 0;
        PyDict_SetItem(counts, ngram, PyLong_FromLong(value + 1));
        Py_DECREF(ngram);
    }

ok:
    return counts;
err:
    if (counts)
    {
        Py_DECREF(counts);
    }
    return NULL;
}

static PyMethodDef module_methods[] = {
    {"count_ngrams", count_ngrams, METH_VARARGS}, {NULL, NULL, 0, NULL}};

static struct PyModuleDef ngram = {PyModuleDef_HEAD_INIT, "ngram",
                                   "Fast ngram operations in C", -1, module_methods};

PyMODINIT_FUNC PyInit_ngram() { return PyModule_Create(&ngram); }
