from setuptools import setup, Extension

module1 = Extension("pb",
                    sources=["pb.c", "deviceapps.pb-c.c"],
                    extra_compile_args=["-g"],
                    libraries=["protobuf-c", "z"],
                    library_dirs=["/usr/lib"],
                    include_dirs=["/usr/include/google/protobuf-c/"],
                    )

setup(name="pb",
      version="1.0",
      description="Protobuf (de)serializer",
      test_suite="tests",
      ext_modules=[module1])
