import { join } from 'path';
import { existsSync, mkdirSync, rmdirSync, copyFileSync, createWriteStream } from 'fs';
import * as child_process from 'child_process';
import archiver from 'archiver';

async function packageLambda() {
    const tempDir = join(__dirname, 'tmp', 'custom_chunking_lambda_package');
    // const lambdaCodePath = join(__dirname, 'src', 'services', 'CustomChunker', 'custom_chunking_python.py');
    const lambdaCodePath = join(__dirname, 'CustomChunker', 'custom_chunking_lambda_function.py');
    const zipFilePath = join(__dirname, 'lambda_package.zip');

    // Clean up the temp directory if it exists
    if (existsSync(tempDir)) {
        console.log(`Removing existing temporary directory: ${tempDir}`);
        rmdirSync(tempDir, { recursive: true });
    }

    // Create the temp directory
    console.log(`Creating temporary directory: ${tempDir}`);
    mkdirSync(tempDir, { recursive: true });

    // Copy the Lambda code to the temp directory
    console.log(`Copying Lambda code from ${lambdaCodePath} to ${tempDir}`);
    copyFileSync(lambdaCodePath, join(tempDir, 'custom_chunking_lambda_function.py'));

    // Install the required dependencies (e.g., pypdf) into the temp directory
    console.log('Installing dependencies in the temp directory...');
    child_process.execSync('pip install pypdf --target ' + tempDir, { stdio: 'inherit' });

    // Create the zip file for the Lambda package
    console.log(`Creating zip file: ${zipFilePath}`);
    const output = createWriteStream(zipFilePath);
    const archive = archiver('zip', { zlib: { level: 9 } });

    archive.pipe(output);
    archive.directory(tempDir, false);

    // Finalize the archive and return the promise
    return new Promise<void>((resolve, reject) => {
        archive.finalize()
            .then(() => {
                console.log(`Lambda package zip finalized at: ${zipFilePath}`);
                resolve();
            })
            .catch((err) => {
                console.error('Error while creating Lambda package zip:', err);
                reject(err);
            });
    });
}

// Run the packaging script
packageLambda().catch((err) => {
    console.error('Packaging failed:', err);
});

