import platform

from packaging import version

from sourcerer import __version__, package_name
from sourcerer.domain.package_meta.entities import PackageMeta
from sourcerer.domain.package_meta.services import BasePackageMetaService
from sourcerer.utils import get_last_package_version


class PackageMetaService(BasePackageMetaService):
    def get_package_meta(self) -> PackageMeta:
        latest_version = get_last_package_version(package_name)
        has_available_update = (
            version.parse(latest_version) > version.parse(__version__)
            if latest_version
            else False
        )

        return PackageMeta(
            version=__version__,
            latest_version=latest_version,
            has_available_update=has_available_update,
            system_version=platform.release(),
            platform=platform.system(),
        )
