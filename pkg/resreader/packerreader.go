/**
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package resreader

import (
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"os"
	"path"
	"path/filepath"
)

// PackerReader implements ResReader for packer resources
type PackerReader struct {
	allResInfo map[string]ResourceInfo
}

// SetInfo sets the resource info for a resource key'd on the source
func (r PackerReader) SetInfo(source string, resInfo ResourceInfo) {
	r.allResInfo[source] = resInfo
}

func addTfExtension(filename string) {
	newFilename := fmt.Sprintf("%s.tf", filename)
	if err := os.Rename(filename, newFilename); err != nil {
		log.Fatalf(
			"failed to add .tf extension to %s needed to get info on packer resource: %e",
			filename, err)
	}
}

func getHCLFiles(dir string) []string {
	allFiles, err := ioutil.ReadDir(dir)
	if err != nil {
		log.Fatalf("Failed to read packer source directory %s", dir)
	}
	var hclFiles []string
	for _, f := range allFiles {
		if f.IsDir() {
			continue
		}
		if filepath.Ext(f.Name()) == ".hcl" {
			hclFiles = append(hclFiles, path.Join(dir, f.Name()))
		}
	}
	return hclFiles
}

func copyHCLFilesToTmp(dir string) (string, []string, error) {
	tmpDir, err := ioutil.TempDir("", "pkwriter-*")
	if err != nil {
		return "", []string{}, fmt.Errorf(
			"failed to create temp directory for packer reader")
	}
	hclFiles := getHCLFiles(dir)
	var hclFilePaths []string

	for _, hclFilename := range hclFiles {

		// Open file for copying
		hclFile, err := os.Open(hclFilename)
		if err != nil {
			return "", hclFiles, fmt.Errorf(
				"failed to open packer HCL file %s: %v", hclFilename, err)
		}
		defer hclFile.Close()

		// Create a file to copy to
		destPath := path.Join(tmpDir, path.Base(hclFilename))
		destination, err := os.Create(destPath)
		if err != nil {
			return "", hclFiles, fmt.Errorf(
				"failed to create copy of packer HCL file %s: %v", hclFilename, err)
		}
		defer destination.Close()

		// Copy
		if _, err := io.Copy(destination, hclFile); err != nil {
			return "", hclFiles, fmt.Errorf(
				"failed to copy packer resource at %s to temporary directory to inspect: %v",
				dir, err)
		}
		hclFilePaths = append(hclFilePaths, destPath)
	}
	return tmpDir, hclFilePaths, nil
}

// GetInfo reads the ResourceInfo for a packer module
func (r PackerReader) GetInfo(source string) (ResourceInfo, error) {
	if resInfo, ok := r.allResInfo[source]; ok {
		return resInfo, nil
	}
	tmpDir, packerFiles, err := copyHCLFilesToTmp(source)
	if err != nil {
		return ResourceInfo{}, err
	}
	defer os.RemoveAll(tmpDir)

	for _, packerFile := range packerFiles {
		addTfExtension(packerFile)
	}
	resInfo, err := getHCLInfo(tmpDir)
	if err != nil {
		return resInfo, fmt.Errorf("PackerReader: %v", err)
	}
	r.allResInfo[source] = resInfo
	return resInfo, nil
}
