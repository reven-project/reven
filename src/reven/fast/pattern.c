#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <math.h>
#include <object.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static PyObject *pattern_search(PyObject *self, PyObject *args)
{
    const char *pattern;
    Py_ssize_t pattern_len;
    const char *data;
    Py_ssize_t data_len;
    int step;
    if (!PyArg_ParseTuple(args, "y#y#i", &pattern, &pattern_len, &data,
                          &data_len, &step))
    {
        return NULL;
    }

    PyObject *indices = PyList_New(0);
    if (pattern_len > data_len * 2)
    {
        return indices;
    }
    size_t iters = data_len * 2 - pattern_len + 1;
    for (size_t i = 0; i < iters; i += step)
    {
        bool matches = true;
        for (size_t j = 0; j < pattern_len; j++)
        {
            char a, b;
            if (pattern[j] >= 'a' && pattern[j] <= 'f')
            {
                a = pattern[j] - 'a' + 0xa;
            }
            else if (pattern[j] >= '0' && pattern[j] <= '9')
            {
                a = pattern[j] - '0';
            }
            else if (pattern[j] == '?')
            {
                continue;
            }
            else
            {
                goto err;
            }

            if ((i + j) % 2 == 0)
            {
                b = (data[(i + j) / 2] & 0xF0) >> 4;
            }
            else
            {
                b = (data[(i + j) / 2] & 0xF);
            }
            if (a != b)
            {
                matches = false;
                break;
            }
        }
        if (matches)
        {
            PyList_Append(indices, PyLong_FromSize_t(i / step));
        }
    }
ok:
    return indices;
err:
    PyErr_SetString(PyExc_ValueError, "Unexpected character in pattern");
    Py_DECREF(indices);
    return NULL;
}

static PyMethodDef module_methods[] = {
    {"pattern_search", pattern_search, METH_VARARGS}, {NULL, NULL, 0, NULL}};

static struct PyModuleDef pattern = {PyModuleDef_HEAD_INIT, "pattern",
                                     "Fast pattern operations in C", -1, module_methods};

PyMODINIT_FUNC PyInit_pattern() { return PyModule_Create(&pattern); }
