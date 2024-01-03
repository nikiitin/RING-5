import tarfile
import os
import utils.utils as utils
from tqdm import tqdm

class Compressor:
    _singleton = None
    @classmethod
    def getInstance(cls) -> "Compressor":
        if cls._singleton is None:
            cls._singleton = Compressor()
        return cls._singleton
        
    
    def _compress(self, filesToCompress: list, pathToTar: str, destDir: str) -> None:
        # Create the tar file
        if not utils.checkDirExists(destDir):
            try:
                os.mkdir(destDir)
            except OSError:
                raise RuntimeError("Could not find or create the directory: " + destDir)
        tar = tarfile.open(pathToTar + ".tar.gz", "w:gz")
        # Add all the files to the tar file
        for file in tqdm(filesToCompress):
            # Add the file to the tar
            tar.add(file)
        # Close the tar file
        tar.close()

    def _untar(self, pathToTar: str, destDir: str) -> None:
        # Create the directory
        if not utils.checkDirExists(destDir):
            raise RuntimeError("Could not find the directory: " + self.destDir)
        # Extract the tar file
        try:
            tar = tarfile.open(pathToTar + ".tar.gz", "r:gz")
        except OSError:
            raise RuntimeError("Could not find or open the file: " + destDir + ".tar.gz")

        tar.extractall(destDir)
        tar.close()
    
    def __call__(self,
        filesToCompress: list,
        destDir: str,
        fileName: str,
        finalUntar: bool = True) -> None:
        pathToTar = os.path.join(destDir, fileName)
        # Compress the files
        print("Compressing files...")
        print("Files to compress: " + str(len(filesToCompress)))
        self._compress(filesToCompress, pathToTar, destDir)
        # Untar the files
        if finalUntar:
            self._untar(pathToTar, destDir)
