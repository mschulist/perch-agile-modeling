'use client'

import { useEffect, useState } from 'react'
import { postServerRequest } from '@/networking/server_requests'
import { getCurrentProject } from '../navigation/ProjectSelector'
import { MultiSelect } from '../examineAnnotations/MultiSelect'
import { SearchFromFile } from './SearchFromFile'
import { ALL_SPECIES_CODES } from '@/lib/allSpeciesCodes'

export function Search() {
  const [speciesCodes, setSpeciesCodes] = useState<string[]>([])
  const [call_types, setCallTypes] = useState<string[]>([])
  const [allSpeciesCodes, setAllSpeciesCodes] = useState<string[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [numTargets, setNumTargets] = useState<number>(3)
  const [numExPerTarget, setNumExPerTarget] = useState<number>(5)
  const [searchSuccess, setSearchSuccess] = useState<string>('')

  useEffect(() => {
    getAllSpeciesCodes().then((codes) => {
      setAllSpeciesCodes(codes)
    })
  }, [])

  async function handleSearch() {
    const [validCodes, errorCodes] = checkSpeciesCodes(
      speciesCodes,
      allSpeciesCodes
    )
    const invalidCallTypes = checkCallTypes(call_types)
    if (call_types.length === 0 || speciesCodes.length === 0) {
      setErrorMessage('Please select at least one species code and call type.')
      return
    }
    if (!validCodes && invalidCallTypes.length !== 0) {
      setErrorMessage(
        `Invalid species codes: {${errorCodes.join(', ')}} and call types: {${invalidCallTypes.join(', ')}}. Please check your input.`
      )
      return
    }
    if (!validCodes) {
      setErrorMessage(
        `Invalid species codes: {${errorCodes.join(', ')}}. Please check your input.`
      )
      return
    }
    if (invalidCallTypes.length !== 0) {
      setErrorMessage(
        `Invalid call types: {${invalidCallTypes.join(', ')}}. Please check your input.`
      )
      return
    }
    setErrorMessage(null)
    const res = await postSearchRequest(
      speciesCodes,
      call_types,
      numTargets,
      numExPerTarget
    )
    if (res.status !== 200) {
      setErrorMessage('Search request failed')
      return
    } else {
      const response = await res.json()
      setSearchSuccess(response.message)
    }
  }

  return (
    <div className='flex flex-col items-center h-5/6 gap-3'>
      <div className='w-1/2 flex flex-col items-center gap-3'>
        <h1 className='text-xl'>Upload a text file of species codes</h1>
        <SearchFromFile setSpeciesCodes={setSpeciesCodes} />
        <h2 className='text-lg'>Or manually enter below...</h2>
      </div>
      <div className='w-1/2'>
        <MultiSelect
          options={[]}
          setLabels={setSpeciesCodes}
          labels={speciesCodes}
          placeholder='Species codes'
        />
      </div>
      <div className='w-1/2'>
        <MultiSelect
          options={[]}
          setLabels={setCallTypes}
          labels={call_types}
          placeholder='Call types'
        />
      </div>
      <div className='w-1/4 flex flex-col items-center gap-4'>
        <div className='flex flex-col items-center gap-2'>
          <p className='text-lg'>Number of examples per target:</p>
          <input
            aria-label='numExPerTarget'
            type='number'
            value={numExPerTarget}
            onChange={(e) => {
              const value = Math.min(Math.max(1, parseInt(e.target.value)), 15)
              setNumExPerTarget(isNaN(value) ? 1 : value)
            }}
            className='input input-bordered w-24'
          />
        </div>
        <div className='flex flex-col items-center gap-2'>
          <p className='text-lg'>Number of Targets:</p>
          <input
            aria-label='numTargets'
            type='number'
            value={numTargets}
            onChange={(e) => {
              const value = Math.min(Math.max(1, parseInt(e.target.value)), 10)
              setNumTargets(isNaN(value) ? 1 : value)
            }}
            className='input input-bordered w-24'
          />
        </div>
      </div>
      <button className='btn btn-primary' onClick={handleSearch}>
        Search
      </button>
      {errorMessage && <p className='text-red-500'>{errorMessage}</p>}
      {searchSuccess && <p className='text-green-500'>{searchSuccess}</p>}
    </div>
  )
}

async function getAllSpeciesCodes() {
  return ALL_SPECIES_CODES
  // const res = await getServerRequest('all_species_codes')
  // const response = await res.json()
  // if (res.status === 200) {
  //   return response.species_codes
  // }
  // throw new Error(response.error)
}

function checkSpeciesCodes(
  speciesCodes: string[],
  allSpeciesCodes: string[]
): [boolean, string[]] {
  const invalidCodes = speciesCodes.filter(
    (code) => !allSpeciesCodes.includes(code)
  )
  if (invalidCodes.length === 0) {
    return [true, []]
  }
  return [false, invalidCodes]
}

async function postSearchRequest(
  speciesCodes: string[],
  callTypes: string[],
  numTargets: number,
  numExPerTarget: number
) {
  const projectId = getCurrentProject()?.id
  if (!projectId) {
    throw new Error('No project selected')
  }
  const res = await postServerRequest(
    `gather_possible_examples?project_id=${projectId}&num_examples_per_target=${numExPerTarget}&num_targets=${numTargets}`,
    {
      species_codes: speciesCodes,
      call_types: callTypes,
    }
  )
  return res
}

function checkCallTypes(callTypes: string[]) {
  const allowedCallTypes = ['call', 'song']
  return callTypes.filter((type) => !allowedCallTypes.includes(type))
}
