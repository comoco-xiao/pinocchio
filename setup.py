import os
import subprocess
import sys
from pathlib import Path
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext

PROJECT_DIR = Path(__file__).parent
VERSION = "3.4.0"

class CMakeBuildExt(build_ext):
    """集成 CMake 编译流程"""
    user_options = build_ext.user_options + [
        ('build-type=', None, 'CMake build type [Release|Debug]'),
    ]

    def initialize_options(self):
        super().initialize_options()
        self.build_type = "Release"

    def finalize_options(self):
        super().finalize_options()

    def run(self):
        self._check_dependencies()
        self._configure_and_build()

    def _check_dependencies(self):
        """检查编译依赖"""
        required_commands = {
            'cmake': 'CMake >= 3.10',
            'make': 'Make/Ninja'
        }
        missing = []
        for cmd, desc in required_commands.items():
            try:
                subprocess.check_output([cmd, '--version'], stderr=subprocess.DEVNULL)
            except OSError:
                missing.append(desc)
        if missing:
            sys.stderr.write(f"Error: Missing required tools: {', '.join(missing)}\n")
            sys.exit(1)

    def _configure_and_build(self):
        """执行 CMake 构建"""
        build_dir = Path(self.build_temp) / "cmake_build"
        install_dir = Path(self.build_lib).absolute()

        # 创建构建目录
        build_dir.mkdir(parents=True, exist_ok=True)

        # Homebrew 安装的 Boost 路径
        boost_root = "/home/ubuntu/workspace/pkg/boost_1_87_0"
    
        # CMake 配置参数
        cmake_args = [
            f"-DCMAKE_INSTALL_PREFIX={install_dir}",
            f"-DCMAKE_BUILD_TYPE={self.build_type}",
            "-DBUILD_PYTHON_INTERFACE=ON",
            "-DBUILD_TESTING=OFF",
            "-DBUILD_WITH_COLLISION_SUPPORT=ON",
            f"-DPYTHON_EXECUTABLE={sys.executable}",
            
            # 显式指定 Boost 路径
            f"-DBOOST_ROOT={boost_root}",
            f"-DBoost_NO_SYSTEM_PATHS=ON",
            
            # 强制使用动态链接库
            "-DBoost_USE_STATIC_LIBS=OFF",
            "-DBoost_USE_STATIC_RUNTIME=OFF"
        ]

        # 生成构建系统
        subprocess.check_call(
            ["cmake", str(PROJECT_DIR)] + cmake_args,
            cwd=str(build_dir)
        )

        # 编译并安装
        build_args = ["--build", ".", "--target", "install"]
        if self.build_type == "Release":
            build_args += ["--config", "Release", "-j2"]
        subprocess.check_call(
            ["cmake"] + build_args,
            cwd=str(build_dir)
        )

setup(
    name="pinocchio",
    version=VERSION,
    description="Efficient Rigid Body Dynamics Library",
    author="Pinocchio Contributors",
    license="BSD-2-Clause",
    packages=["pinocchio"],
    python_requires=">=3.6",
    install_requires=["numpy"],
    ext_modules=[Extension("pinocchio_dummy", [])],  # 触发扩展构建
    cmdclass={"build_ext": CMakeBuildExt},
    zip_safe=False,
)