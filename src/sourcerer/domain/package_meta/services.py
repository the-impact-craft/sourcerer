from abc import ABCMeta, abstractmethod

from sourcerer.domain.package_meta.entities import PackageMeta


class BasePackageMetaService(metaclass=ABCMeta):
    @abstractmethod
    def get_package_meta(self) -> PackageMeta:
        raise NotImplementedError
