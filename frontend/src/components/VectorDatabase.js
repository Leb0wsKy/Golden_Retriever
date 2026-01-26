import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
} from '@mui/material';
import { Add as AddIcon, Search as SearchIcon } from '@mui/icons-material';
import axios from 'axios';

function VectorDatabase() {
  const [collections, setCollections] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [newCollection, setNewCollection] = useState({
    name: '',
    dimension: 384,
    distance: 'cosine',
  });

  useEffect(() => {
    fetchCollections();
  }, []);

  const fetchCollections = async () => {
    try {
      const response = await axios.get('/api/collections');
      setCollections(response.data);
    } catch (error) {
      console.error('Error fetching collections:', error);
    }
  };

  const handleCreateCollection = async () => {
    try {
      await axios.post('/api/collections', newCollection);
      setOpenDialog(false);
      fetchCollections();
      setNewCollection({ name: '', dimension: 384, distance: 'cosine' });
    } catch (error) {
      console.error('Error creating collection:', error);
    }
  };

  const handleSearch = async () => {
    try {
      const response = await axios.post('/api/search', {
        query: searchQuery,
        limit: 10,
      });
      setSearchResults(response.data);
    } catch (error) {
      console.error('Error searching:', error);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Vector Database</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpenDialog(true)}
        >
          Create Collection
        </Button>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Search Vectors
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            fullWidth
            label="Search Query"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <Button
            variant="contained"
            startIcon={<SearchIcon />}
            onClick={handleSearch}
          >
            Search
          </Button>
        </Box>
        {searchResults.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2">Results:</Typography>
            {searchResults.map((result, index) => (
              <Paper key={index} sx={{ p: 1, mt: 1 }}>
                <Typography variant="body2">
                  Score: {result.score} - {result.text}
                </Typography>
              </Paper>
            ))}
          </Box>
        )}
      </Paper>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Collection Name</TableCell>
              <TableCell>Vectors Count</TableCell>
              <TableCell>Dimension</TableCell>
              <TableCell>Distance Metric</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {collections.map((collection) => (
              <TableRow key={collection.name}>
                <TableCell>{collection.name}</TableCell>
                <TableCell>{collection.vectors_count}</TableCell>
                <TableCell>{collection.dimension}</TableCell>
                <TableCell>{collection.distance}</TableCell>
                <TableCell>
                  <Chip
                    label={collection.status}
                    color={collection.status === 'active' ? 'success' : 'default'}
                    size="small"
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)}>
        <DialogTitle>Create New Collection</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Collection Name"
            fullWidth
            value={newCollection.name}
            onChange={(e) => setNewCollection({ ...newCollection, name: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Vector Dimension"
            type="number"
            fullWidth
            value={newCollection.dimension}
            onChange={(e) => setNewCollection({ ...newCollection, dimension: parseInt(e.target.value) })}
          />
          <TextField
            margin="dense"
            label="Distance Metric"
            select
            fullWidth
            value={newCollection.distance}
            onChange={(e) => setNewCollection({ ...newCollection, distance: e.target.value })}
            SelectProps={{
              native: true,
            }}
          >
            <option value="cosine">Cosine</option>
            <option value="euclidean">Euclidean</option>
            <option value="dot">Dot Product</option>
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateCollection} variant="contained">
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default VectorDatabase;
